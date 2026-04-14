from __future__ import annotations

import asyncio
import copy
import math
from datetime import date
from pathlib import Path

from loguru import logger

from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError, HybridTaskConfig
from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig
from zhy.modules.fetch.folder_patents_api import RequestScheduler, post_page_async
from zhy.modules.persist.json_io import load_json_file_any_utf, save_json
from zhy.modules.persist.page_path import (
    build_monthly_page_output_path,
    build_monthly_run_summary_path,
    has_existing_page_files,
)


def parse_month_bounds(month_text: str) -> tuple[date, date]:
    """简介：把 YYYY-MM 文本转换成当月起始日和下月起始日。
    参数：month_text 为 YYYY-MM 格式月份文本。
    返回值：(month_start, next_month_start)。
    逻辑：后续所有专利是否命中目标月份，都统一基于这个半开区间判断。
    """

    year_text, month_part = month_text.split("-")
    year = int(year_text)
    month = int(month_part)
    month_start = date(year, month, 1)
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    return month_start, next_month_start


def parse_publication_date(value: object) -> date | None:
    """简介：解析专利 PBD 文本。
    参数：value 为原始 PBD 字段值。
    返回值：成功时返回 date，失败时返回 None。
    """

    text = str(value or "").strip()
    if len(text) != 10:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def is_date_in_target_month(publication_date: date, month_start: date, next_month_start: date) -> bool:
    return month_start <= publication_date < next_month_start


def filter_patents_for_target_month(rows: list[dict], month_start: date, next_month_start: date) -> list[dict]:
    """简介：从单页专利列表中过滤出目标月份的数据。
    参数：rows 为单页 patents_data；month_start 和 next_month_start 为目标月份范围。
    返回值：仅包含目标月份专利的新列表。
    """

    matched_rows: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        publication_date = parse_publication_date(row.get("PBD"))
        if publication_date is None:
            continue
        if is_date_in_target_month(publication_date, month_start, next_month_start):
            matched_rows.append(row)
    return matched_rows


def get_page_publication_date_bounds(rows: list[dict]) -> tuple[date | None, date | None]:
    """简介：获取单页专利列表里的最新和最旧公开日期。
    参数：rows 为单页 patents_data。
    返回值：(newest_date, oldest_date)。
    """

    dates = [parse_publication_date(row.get("PBD")) for row in rows if isinstance(row, dict)]
    valid_dates = [item for item in dates if item is not None]
    if not valid_dates:
        return None, None
    return max(valid_dates), min(valid_dates)


def build_monthly_patents_request_body(
    template: dict,
    *,
    space_id: str,
    folder_id: str,
    page: int,
    size: int,
    sort: str,
    view_type: str,
    is_init: bool,
    standard_only: bool,
) -> dict:
    """简介：基于模板构建按月抓取专利的请求体。
    参数：template 为已捕获的原始 body 模板；其余参数为当前页面和排序控制参数。
    返回值：可直接提交的请求体字典。
    """

    body = copy.deepcopy(template)
    body["space_id"] = space_id
    body["folder_id"] = folder_id
    body["page"] = page if isinstance(body.get("page"), int) else str(page)
    body["size"] = size
    body["sort"] = sort
    body["view_type"] = view_type
    body["is_init"] = is_init
    body["standard_only"] = standard_only
    return body


def build_monthly_page_output_payload(parsed: dict, matched_rows: list[dict], source_page_number: int, month_text: str) -> dict:
    """简介：把命中目标月份的数据写成新的页级输出结构。
    参数：parsed 为原始接口响应；matched_rows 为筛选后的记录；source_page_number 为原始请求页码；month_text 为目标月份文本。
    返回值：适合写入 page_XXXX.json 的 payload。
    """

    payload = copy.deepcopy(parsed) if isinstance(parsed, dict) else {}
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}
        payload["data"] = data
    data["patents_data"] = matched_rows
    data["month_filter"] = month_text
    data["source_page_number"] = source_page_number
    data["matched_patent_count"] = len(matched_rows)
    return payload


def filter_folder_items_for_test(folder_items: list[dict], test_folder_ids: list[str]) -> list[dict]:
    """简介：按测试 folder_id 白名单过滤竞争对手列表。
    参数：folder_items 为候选公司列表；test_folder_ids 为允许抓取的 folder_id 列表。
    返回值：过滤后的公司列表。
    逻辑：白名单为空时直接返回全部；有值时只保留命中的公司。
    """

    normalized_ids = {str(item).strip() for item in test_folder_ids if str(item).strip()}
    if not normalized_ids:
        return folder_items
    return [
        item for item in folder_items
        if isinstance(item, dict) and str(item.get("folder_id") or "").strip() in normalized_ids
    ]


def build_existing_output_skip_summary(*, output_root: Path, space_id: str, folder_item: dict) -> dict:
    folder_id = str(folder_item.get("folder_id") or "").strip()
    folder_name = str(folder_item.get("folder_name") or "").strip()
    folder_dir = output_root / f"{space_id}_{folder_id}"
    return {
        "space_id": space_id,
        "folder_id": folder_id,
        "folder_name": folder_name,
        "status": "skipped_existing_output",
        "reason": "existing_page_files_detected",
        "requested_pages": 0,
        "pages_saved": 0,
        "matched_patent_count": 0,
        "skipped_too_new_pages": 0,
        "saved_files": [str(path) for path in sorted(folder_dir.glob("page_*.json")) if path.is_file()],
        "error": None,
        "auth_refresh_count": 0,
    }


async def fetch_monthly_patents_for_folder(
    *,
    config: CompetitorPatentPipelineConfig,
    scheduler: RequestScheduler,
    headers: dict[str, str],
    auth_template: dict,
    space_id: str,
    folder_item: dict,
) -> dict:
    """简介：按目标月份抓取单个竞争对手文件夹的专利数据。
    参数：config 为总流程配置；scheduler 为请求调度器；headers 为当前鉴权头；auth_template 为已捕获的请求体模板；space_id 和 folder_item 为当前公司标识。
    返回值：单个文件夹抓取 summary。
    逻辑：按 PBD 倒序逐页抓取，整页太新则跳过，整页太旧则停止，命中月份时只保存命中记录。
    """

    folder_id = str(folder_item.get("folder_id") or "").strip()
    folder_name = str(folder_item.get("folder_name") or "").strip()
    output_root = config.original_output_root
    request_url = f"https://workspace-service.zhihuiya.com/workspace/web/{space_id}/folder/{folder_id}/patents"
    month_start, next_month_start = parse_month_bounds(config.month)
    proxies = {"http": config.patents_proxy, "https": config.patents_proxy} if config.patents_proxy else None

    summary = {
        "space_id": space_id,
        "folder_id": folder_id,
        "folder_name": folder_name,
        "status": "ok",
        "reason": "",
        "requested_pages": 0,
        "pages_saved": 0,
        "matched_patent_count": 0,
        "skipped_too_new_pages": 0,
        "saved_files": [],
        "error": None,
    }

    next_page = config.patents_start_page
    while True:
        body = build_monthly_patents_request_body(
            auth_template,
            space_id=space_id,
            folder_id=folder_id,
            page=next_page,
            size=config.patents_page_size,
            sort=config.patents_sort,
            view_type=config.patents_view_type,
            is_init=config.patents_is_init,
            standard_only=config.patents_standard_only,
        )
        summary["requested_pages"] += 1

        _, parsed = await post_page_async(
            page=next_page,
            url=request_url,
            headers=headers,
            body=body,
            timeout_seconds=config.patents_timeout_seconds,
            proxies=proxies,
            scheduler=scheduler,
            retry_count=config.patents_retry_count,
            retry_backoff_base_seconds=config.patents_retry_backoff_base_seconds,
        )

        data = parsed.get("data") if isinstance(parsed, dict) else None
        if not isinstance(data, dict):
            summary["status"] = "error"
            summary["reason"] = "missing_data_object"
            break

        patents_data = data.get("patents_data")
        if not isinstance(patents_data, list) or not patents_data:
            summary["reason"] = "empty_page_detected"
            break

        newest_date, oldest_date = get_page_publication_date_bounds(patents_data)
        if newest_date is None or oldest_date is None:
            summary["reason"] = "page_missing_pbd"
            break

        # 整页都是目标月份之后的数据，跳过继续往后翻页。
        if oldest_date >= next_month_start:
            summary["skipped_too_new_pages"] += 1
            next_page += 1
            continue

        # 整页都早于目标月份，不可能再找到目标月份数据，停止。
        if newest_date < month_start:
            summary["reason"] = (
                "first_page_too_old_skip_folder"
                if next_page == config.patents_start_page and summary["pages_saved"] == 0
                else "reached_too_old_page"
            )
            break

        matched_rows = filter_patents_for_target_month(patents_data, month_start, next_month_start)
        if matched_rows:
            output_path = build_monthly_page_output_path(output_root, space_id, folder_id, next_page)
            output_payload = build_monthly_page_output_payload(parsed, matched_rows, next_page, config.month)
            save_json(output_path, output_payload)
            summary["saved_files"].append(str(output_path))
            summary["pages_saved"] += 1
            summary["matched_patent_count"] += len(matched_rows)

        # 最旧日期已经落入目标月份之前，跨越了月份边界，停止。
        if oldest_date < month_start:
            summary["reason"] = "crossed_below_target_month"
            break

        total = data.get("total")
        limit = data.get("limit")
        try:
            total_int = int(total) if total is not None else None
        except (TypeError, ValueError):
            total_int = None
        try:
            limit_int = int(limit) if limit is not None else None
        except (TypeError, ValueError):
            limit_int = None

        if total_int is not None and limit_int and limit_int > 0:
            max_page_by_total = math.ceil(total_int / limit_int)
            if next_page >= max_page_by_total:
                summary["reason"] = "reached_total_page"
                break

        next_page += 1

    if not summary["reason"]:
        summary["reason"] = "completed_without_explicit_stop_reason"
    return summary


async def run_monthly_patent_fetch(
    *,
    config: CompetitorPatentPipelineConfig,
    managed,
    folder_mapping_file: Path,
    auth_config: HybridTaskConfig,
) -> tuple[Path, dict]:
    """简介：按目标月份抓取所有竞争对手文件夹的专利数据。
    参数：config 为总流程配置；managed 为浏览器上下文；folder_mapping_file 为已过滤的竞争对手映射文件；auth_config 为鉴权抓取配置（由 task 层构建）。
    返回值：(run_summary_path, run_summary_payload)。
    逻辑：先抓一份可复用鉴权，再逐个公司顺序抓取按月专利；如遇 401，则用当前公司刷新一次鉴权后重试。
    """

    from zhy.modules.fetch.folder_patents_auth import refresh_auth_state

    mapping_payload = load_json_file_any_utf(folder_mapping_file)
    folder_items = mapping_payload.get("data", []) if isinstance(mapping_payload, dict) else []
    valid_items = [item for item in folder_items if isinstance(item, dict) and str(item.get("folder_id") or "").strip()]
    valid_items = filter_folder_items_for_test(valid_items, config.patents_test_folder_ids)
    summary_path = build_monthly_run_summary_path(config.original_output_root, config.month)
    company_concurrency = max(config.patents_company_concurrency, 1)
    run_summary = {
        "month": config.month,
        "space_id": config.workspace_space_id,
        "folder_mapping_file": str(folder_mapping_file),
        "company_concurrency": company_concurrency,
        "test_folder_ids": list(config.patents_test_folder_ids),
        "folders": [],
    }
    save_json(summary_path, run_summary)

    if not valid_items:
        return summary_path, run_summary

    skipped_items: list[dict] = []
    active_items: list[dict] = []
    for folder_item in valid_items:
        folder_id = str(folder_item.get("folder_id") or "").strip()
        folder_dir = config.original_output_root / f"{config.workspace_space_id}_{folder_id}"
        if has_existing_page_files(folder_dir):
            logger.warning(
                "[monthly_patents] skip folder because existing page files detected: folder_id={} folder_dir={}",
                folder_id,
                folder_dir,
            )
            skipped_items.append(
                build_existing_output_skip_summary(
                    output_root=config.original_output_root,
                    space_id=config.workspace_space_id,
                    folder_item=folder_item,
                )
            )
            continue
        active_items.append(folder_item)

    if skipped_items:
        run_summary["folders"].extend(skipped_items)
        save_json(summary_path, run_summary)

    if not active_items:
        return summary_path, run_summary

    scheduler = RequestScheduler(
        concurrency=company_concurrency,
        min_interval_seconds=config.patents_min_request_interval_seconds,
        jitter_seconds=config.patents_request_jitter_seconds,
    )

    auth_state = await refresh_auth_state(
        managed,
        auth_config,
        config.workspace_space_id,
        str(active_items[0].get("folder_id") or "").strip(),
    )
    auth_headers = auth_state.to_headers(
        origin=config.workspace_origin,
        referer=config.workspace_referer,
        user_agent=config.workspace_user_agent,
        x_api_version=config.workspace_x_api_version,
        x_patsnap_from=config.workspace_x_patsnap_from,
        x_site_lang=config.workspace_x_site_lang,
    )
    auth_template = auth_state.body_template if isinstance(auth_state.body_template, dict) else {}

    async def process_single_folder(folder_item: dict) -> dict:
        folder_id = str(folder_item.get("folder_id") or "").strip()
        local_auth_headers = dict(auth_headers)
        local_auth_template = copy.deepcopy(auth_template)
        refresh_count = 0
        while True:
            try:
                folder_summary = await fetch_monthly_patents_for_folder(
                    config=config,
                    scheduler=scheduler,
                    headers=local_auth_headers,
                    auth_template=local_auth_template,
                    space_id=config.workspace_space_id,
                    folder_item=folder_item,
                )
                folder_summary["auth_refresh_count"] = refresh_count
                break
            except AuthRefreshRequiredError:
                if refresh_count >= config.patents_max_auth_refreshes:
                    raise RuntimeError(f"auth refresh retry limit reached for folder {folder_id}")
                refresh_count += 1
                logger.warning(
                    "[monthly_patents] refresh auth for monthly patents: folder_id={} refresh_count={}",
                    folder_id,
                    refresh_count,
                )
                new_auth_state = await refresh_auth_state(
                    managed,
                    auth_config,
                    config.workspace_space_id,
                    folder_id,
                )
                local_auth_headers = new_auth_state.to_headers(
                    origin=config.workspace_origin,
                    referer=config.workspace_referer,
                    user_agent=config.workspace_user_agent,
                    x_api_version=config.workspace_x_api_version,
                    x_patsnap_from=config.workspace_x_patsnap_from,
                    x_site_lang=config.workspace_x_site_lang,
                )
                local_auth_template = new_auth_state.body_template if isinstance(new_auth_state.body_template, dict) else {}
        return folder_summary

    for batch_start in range(0, len(active_items), company_concurrency):
        current_batch = active_items[batch_start: batch_start + company_concurrency]
        batch_results = await asyncio.gather(*(process_single_folder(item) for item in current_batch))
        run_summary["folders"].extend(batch_results)
        save_json(summary_path, run_summary)

    return summary_path, run_summary

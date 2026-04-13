from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from zhy.modules.folder_patents_enrichment.basic_fetch import (
    extract_abstract_from_basic_payload,
    extract_grant_date_from_basic_payload,
    fetch_patent_basic_payload,
)
from zhy.modules.folder_patents_enrichment.models import ExistingOutputEnrichmentConfig
from zhy.modules.folder_patents_hybrid.abstract_fetch import build_abstract_headers
from zhy.modules.folder_patents_hybrid.api_fetch import RequestScheduler
from zhy.modules.folder_patents_hybrid.models import AuthRefreshRequiredError, FolderAuthState, HybridTaskConfig
from zhy.modules.folder_patents_hybrid.storage import load_json_file_any_utf, save_json


def load_auth_state_from_file(path: Path) -> FolderAuthState | None:
    """简介：读取已缓存的鉴权状态，缺失或无效时返回 None。
    参数：path 为鉴权状态文件路径。
    返回值：FolderAuthState 或 None。
    逻辑：当前流程允许无缓存启动，因此把文件缺失视为正常情况。
    """

    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    auth_state = FolderAuthState.from_json(payload)
    if not auth_state.authorization and not auth_state.cookie_header:
        return None
    return auth_state


def iter_input_page_files(input_root: Path) -> list[Path]:
    return sorted(path for path in input_root.rglob("page_*.json") if path.is_file())


def parse_space_folder_from_parent(folder_dir: Path) -> tuple[str, str]:
    name = folder_dir.name
    if "_" not in name:
        return "", name
    return name.split("_", 1)


def build_output_path(output_root: Path, input_root: Path, page_file: Path) -> Path:
    relative_path = page_file.relative_to(input_root)
    output_path = output_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def has_granted_status(legal_status: object) -> bool:
    if isinstance(legal_status, list):
        return any(str(item).strip() == "3" for item in legal_status)
    return str(legal_status).strip() == "3"


def build_auth_refresh_config(config: ExistingOutputEnrichmentConfig) -> HybridTaskConfig:
    """简介：把 enrichment 配置映射为 auth_capture 可用的 HybridTaskConfig。
    参数：config 为补充流程配置。
    返回值：仅用于登录和鉴权抓取的 HybridTaskConfig。
    逻辑：复用已有 auth_capture 模块，避免重复实现浏览器登录与请求监听。
    """

    return HybridTaskConfig(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
        cookie_file=config.cookie_file,
        auth_state_file=config.auth_state_file,
        output_root=config.output_root,
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        login_timeout_seconds=config.login_timeout_seconds,
        login_poll_interval_seconds=config.login_poll_interval_seconds,
        origin=config.analytics_origin,
        referer=config.analytics_referer,
        x_site_lang=config.x_site_lang,
        x_api_version=config.x_api_version,
        x_patsnap_from=config.analytics_x_patsnap_from,
        user_agent=config.user_agent,
        abstract_request_url=config.abstract_request_url,
        abstract_origin=config.analytics_origin,
        abstract_referer=config.analytics_referer,
        abstract_x_patsnap_from=config.analytics_x_patsnap_from,
        abstract_request_template=config.abstract_request_template,
        abstract_text_field_name="ABST",
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=100,
        timeout_seconds=config.timeout_seconds,
        capture_timeout_ms=config.capture_timeout_ms,
        max_auth_refreshes=config.max_auth_refreshes,
        retry_count=config.retry_count,
        retry_backoff_base_seconds=config.retry_backoff_base_seconds,
        min_request_interval_seconds=config.min_request_interval_seconds,
        request_jitter_seconds=config.request_jitter_seconds,
        resume=config.resume,
        proxy=config.proxy,
        headless=config.headless,
        fail_fast=False,
    )


async def ensure_auth_state(
    *,
    config: ExistingOutputEnrichmentConfig,
    managed,
    page_files: list[Path],
    auth_state: FolderAuthState | None,
) -> FolderAuthState:
    """简介：确保当前流程拥有可用鉴权状态。
    参数：包含流程配置、浏览器上下文、输入页列表和当前缓存鉴权。
    返回值：可用的 FolderAuthState。
    逻辑：优先复用现有缓存；若不存在，则从首个输入页对应 folder 触发一次鉴权抓取。
    """

    if auth_state is not None:
        return auth_state
    if not page_files:
        raise ValueError("no page files found under input root")

    space_id, folder_id = parse_space_folder_from_parent(page_files[0].parent)
    if not space_id or not folder_id:
        raise ValueError(f"unable to parse space_id/folder_id from {page_files[0].parent}")

    logger.info(
        "[folder_patents_enrichment_workflow] auth cache missing, capture from browser context: space_id={} folder_id={}",
        space_id,
        folder_id,
    )
    from zhy.modules.folder_patents_hybrid.auth_capture import refresh_auth_state

    return await refresh_auth_state(
        managed,
        build_auth_refresh_config(config),
        space_id,
        folder_id,
    )


def build_request_headers(config: ExistingOutputEnrichmentConfig, auth_state: FolderAuthState) -> tuple[dict[str, str], dict[str, str]]:
    """简介：基于当前鉴权状态构建摘要和 basic 请求头。
    参数：config 为流程配置；auth_state 为当前鉴权状态。
    返回值：摘要请求头、basic 请求头。
    逻辑：两类接口当前共用 analytics 场景头部和 token/cookie。
    """

    abstract_headers = build_abstract_headers(
        auth_state=auth_state,
        origin=config.analytics_origin,
        referer=config.analytics_referer,
        user_agent=config.user_agent,
        x_api_version=config.x_api_version,
        x_patsnap_from=config.analytics_x_patsnap_from,
        x_site_lang=config.x_site_lang,
    )
    basic_headers = dict(abstract_headers)
    return abstract_headers, basic_headers


async def build_page_supplement_payload(
    *,
    page_payload: dict,
    page_file: Path,
    space_id: str,
    folder_id: str,
    abstract_headers: dict[str, str],
    basic_headers: dict[str, str],
    config: ExistingOutputEnrichmentConfig,
    scheduler: RequestScheduler,
    proxies: dict[str, str] | None,
) -> dict:
    """简介：为单页现有专利数据生成最小补充信息载荷。
    参数：包含原页数据、上下文标识、请求头和流程配置。
    返回值：仅含 ABST/ISD 的页级输出字典。
    逻辑：逐条读取 PATENT_ID；摘要始终尝试补抓，授权日期仅在 LEGAL_STATUS 含 3 时请求。
    """

    rows = page_payload.get("data", {}).get("patents_data", [])
    if not isinstance(rows, list):
        raise ValueError("data.patents_data is not a list")

    async def process_row(row_index: int, row: object) -> tuple[int, dict, list[dict]]:
        row_failures: list[dict] = []
        if not isinstance(row, dict):
            return row_index, {"PATENT_ID": "", "PN": "", "ABST": "", "ISD": ""}, [
                {"row_index": row_index, "patent_id": "", "reason": "row_not_object"}
            ]

        patent_id = str(row.get("PATENT_ID") or "").strip()
        pn = str(row.get("PN") or "").strip()
        record = {
            "PATENT_ID": patent_id,
            "PN": pn,
            "ABST": "",
            "ISD": "",
        }

        if not patent_id:
            row_failures.append({"row_index": row_index, "patent_id": "", "reason": "missing_patent_id"})
            return row_index, record, row_failures

        try:
            basic_payload = await fetch_patent_basic_payload(
                patent_id=patent_id,
                headers=basic_headers,
                body_template=config.basic_request_body_template,
                timeout_seconds=config.timeout_seconds,
                proxies=proxies,
                scheduler=scheduler,
                retry_count=config.retry_count,
                retry_backoff_base_seconds=config.retry_backoff_base_seconds,
            )
            record["ABST"] = extract_abstract_from_basic_payload(basic_payload)
            if has_granted_status(row.get("LEGAL_STATUS")):
                record["ISD"] = extract_grant_date_from_basic_payload(basic_payload)
        except AuthRefreshRequiredError:
            raise
        except Exception as exc:
            row_failures.append({"row_index": row_index, "patent_id": patent_id, "reason": f"basic: {exc}"})

        return row_index, record, row_failures

    worker_limit = max(int(config.request_concurrency), 1)
    semaphore = asyncio.Semaphore(worker_limit)

    async def guarded_process_row(row_index: int, row: object) -> tuple[int, dict, list[dict]]:
        async with semaphore:
            return await process_row(row_index, row)

    results = await asyncio.gather(
        *(guarded_process_row(index, row) for index, row in enumerate(rows))
    )
    results.sort(key=lambda item: item[0])

    records: list[dict] = [record for _, record, _ in results]
    failures: list[dict] = []
    for _, _, row_failures in results:
        failures.extend(row_failures)

    return {
        "space_id": space_id,
        "folder_id": folder_id,
        "source_file": str(page_file),
        "record_count": len(records),
        "records": records,
        "failures": failures,
    }


async def run_existing_output_enrichment(config: ExistingOutputEnrichmentConfig) -> Path:
    """简介：扫描现有 hybrid 输出并镜像生成仅含 ABST/ISD 的补充目录。
    参数：config 为完整流程配置。
    返回值：运行汇总 summary 文件路径。
    逻辑：建立浏览器上下文 -> 确保鉴权 -> 遍历 page 文件 -> 请求摘要与授权日期 -> 写入镜像输出与汇总。
    """

    if not config.input_root.exists():
        raise FileNotFoundError(f"input root not found: {config.input_root}")

    page_files = iter_input_page_files(config.input_root)
    scheduler = RequestScheduler(
        concurrency=max(int(config.request_concurrency), 1),
        min_interval_seconds=config.min_request_interval_seconds,
        jitter_seconds=config.request_jitter_seconds,
    )
    proxies = {"http": config.proxy, "https": config.proxy} if config.proxy else None

    summary = {
        "input_root": str(config.input_root),
        "output_root": str(config.output_root),
        "auth_state_file": str(config.auth_state_file),
        "total_page_files": len(page_files),
        "pages_written": 0,
        "pages_skipped": 0,
        "pages_failed": 0,
        "files": [],
    }
    summary_path = config.output_root / "run_summary.json"
    save_json(summary_path, summary)

    from playwright.async_api import async_playwright
    from zhy.modules.browser_context.browser_context_workflow import BrowserContextUserInput
    from zhy.modules.browser_context.runtime import build_browser_context
    from zhy.modules.folder_patents_hybrid.auth_capture import refresh_auth_state

    browser_input = BrowserContextUserInput(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
    )

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=browser_input,
            headless=config.headless,
        )
        try:
            auth_state = await ensure_auth_state(
                config=config,
                managed=managed,
                page_files=page_files,
                auth_state=load_auth_state_from_file(config.auth_state_file),
            )

            refresh_count = 0
            for page_file in page_files:
                output_path = build_output_path(config.output_root, config.input_root, page_file)
                if config.resume and output_path.exists():
                    summary["pages_skipped"] += 1
                    summary["files"].append({"input_file": str(page_file), "output_file": str(output_path), "status": "skipped"})
                    save_json(summary_path, summary)
                    continue

                try:
                    while True:
                        abstract_headers, basic_headers = build_request_headers(config, auth_state)
                        page_payload = load_json_file_any_utf(page_file)
                        space_id, folder_id = parse_space_folder_from_parent(page_file.parent)
                        try:
                            supplement_payload = await build_page_supplement_payload(
                                page_payload=page_payload,
                                page_file=page_file,
                                space_id=space_id,
                                folder_id=folder_id,
                                abstract_headers=abstract_headers,
                                basic_headers=basic_headers,
                                config=config,
                                scheduler=scheduler,
                                proxies=proxies,
                            )
                            break
                        except AuthRefreshRequiredError:
                            if refresh_count >= config.max_auth_refreshes:
                                raise RuntimeError("auth refresh retry limit reached")
                            refresh_count += 1
                            auth_state = await refresh_auth_state(
                                managed,
                                build_auth_refresh_config(config),
                                space_id,
                                folder_id,
                            )

                    save_json(output_path, supplement_payload)
                    summary["pages_written"] += 1
                    summary["files"].append(
                        {
                            "input_file": str(page_file),
                            "output_file": str(output_path),
                            "status": "ok",
                            "failure_count": len(supplement_payload["failures"]),
                        }
                    )
                except Exception as exc:
                    logger.exception("[folder_patents_enrichment_workflow] page failed: {}", page_file)
                    summary["pages_failed"] += 1
                    summary["files"].append(
                        {
                            "input_file": str(page_file),
                            "output_file": str(output_path),
                            "status": "error",
                            "error": str(exc),
                        }
                    )

                save_json(summary_path, summary)
        finally:
            await managed.close()

    save_json(summary_path, summary)
    return summary_path

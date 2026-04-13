from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from zhy.modules.competitor_patent_pipeline.monthly_fetch import run_monthly_patent_fetch
from zhy.modules.competitor_patent_pipeline.models import CompetitorPatentPipelineConfig
from zhy.modules.competitor_patent_report import CompetitorPatentReportConfig, run_competitor_patent_report
from zhy.modules.folder_patents_enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.folder_patents_enrichment.workflow import run_existing_output_enrichment
from zhy.modules.folder_patents_hybrid.storage import save_json


def build_pipeline_summary_payload(
    config: CompetitorPatentPipelineConfig,
    *,
    login_status: str,
    login_final_url: str,
    competitor_list_status: str,
    competitor_list_count: int,
    competitor_list_output: str,
    monthly_patents_status: str,
    monthly_patents_folder_count: int,
    monthly_patents_output: str,
    enrich_patents_status: str,
    enrich_patents_output: str,
    enrich_patents_pages_written: int,
    build_monthly_report_status: str,
    build_monthly_report_output: str,
) -> dict:
    """简介：构建竞争对手专利总流程的阶段性 summary 数据。
    参数：config 为总流程配置；login_status 为登录步骤状态；login_final_url 为登录完成后的页面 URL；
    competitor_list_status 为竞争对手列表步骤状态；competitor_list_count 为过滤后的有效条目数；competitor_list_output 为结果文件路径。
    返回值：可直接写盘的 summary 字典。
    逻辑：当前先记录登录和竞争对手列表结果，并把后续专利抓取、补充信息、表格构建标记为 pending。
    """

    return {
        "month": config.month,
        "paths": {
            "cookie_file": str(config.cookie_file),
            "auth_state_file": str(config.auth_state_file),
            "original_output_root": str(config.original_output_root),
            "enriched_output_root": str(config.enriched_output_root),
            "folder_mapping_file": str(config.folder_mapping_file),
            "folder_mapping_raw_file": str(config.folder_mapping_raw_file),
            "legal_status_mapping_file": str(config.legal_status_mapping_file),
            "report_output_dir": str(config.report_output_dir),
        },
        "steps": [
            {
                "name": "login",
                "status": login_status,
                "final_url": login_final_url,
            },
            {
                "name": "fetch_competitor_list",
                "status": competitor_list_status,
                "count": competitor_list_count,
                "output": competitor_list_output,
            },
            {
                "name": "fetch_monthly_patents",
                "status": monthly_patents_status,
                "folder_count": monthly_patents_folder_count,
                "output": monthly_patents_output,
            },
            {
                "name": "enrich_patents",
                "status": enrich_patents_status,
                "pages_written": enrich_patents_pages_written,
                "output": enrich_patents_output,
            },
            {
                "name": "build_monthly_report",
                "status": build_monthly_report_status,
                "output": build_monthly_report_output,
            },
        ],
    }


def build_existing_output_enrichment_config(config: CompetitorPatentPipelineConfig) -> ExistingOutputEnrichmentConfig:
    """简介：把总流程配置映射为现有补充信息模块配置。
    参数：config 为总流程配置。
    返回值：ExistingOutputEnrichmentConfig。
    逻辑：沿用总流程已有路径和浏览器参数，直接复用既有 enrichment 模块。
    """

    return ExistingOutputEnrichmentConfig(
        input_root=config.original_output_root,
        output_root=config.enriched_output_root,
        auth_state_file=config.auth_state_file,
        cookie_file=config.cookie_file,
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        login_timeout_seconds=config.login_timeout_seconds,
        login_poll_interval_seconds=config.login_poll_interval_seconds,
        capture_timeout_ms=config.patents_capture_timeout_ms,
        max_auth_refreshes=config.patents_max_auth_refreshes,
        headless=config.headless,
        timeout_seconds=config.patents_timeout_seconds,
        retry_count=config.patents_retry_count,
        retry_backoff_base_seconds=config.patents_retry_backoff_base_seconds,
        min_request_interval_seconds=config.patents_min_request_interval_seconds,
        request_jitter_seconds=config.patents_request_jitter_seconds,
        resume=config.enrichment_resume,
        proxy=config.patents_proxy,
        user_agent=config.workspace_user_agent,
        x_api_version=config.workspace_x_api_version,
        x_site_lang=config.workspace_x_site_lang,
        analytics_origin=config.analytics_origin,
        analytics_referer=config.analytics_referer,
        analytics_x_patsnap_from=config.analytics_x_patsnap_from,
        abstract_request_url=config.abstract_request_url,
        abstract_request_template=config.abstract_request_template,
        basic_request_body_template=config.basic_request_body_template,
        request_concurrency=config.enrichment_request_concurrency,
    )


def build_competitor_patent_report_config(config: CompetitorPatentPipelineConfig) -> CompetitorPatentReportConfig:
    """简介：把总流程配置映射为现有月报模块配置。
    参数：config 为总流程配置。
    返回值：CompetitorPatentReportConfig。
    逻辑：复用总流程阶段输出路径，避免任务层重复拼装参数。
    """

    return CompetitorPatentReportConfig(
        month=config.month,
        original_root=config.original_output_root,
        enriched_root=config.enriched_output_root,
        folder_mapping_file=config.folder_mapping_file,
        legal_status_mapping_file=config.legal_status_mapping_file,
        output_dir=config.report_output_dir,
    )


def load_enrichment_pages_written(summary_path: Path) -> int:
    """简介：从补充信息 summary 中读取成功写入页数。
    参数：summary_path 为 enrichment 汇总文件路径。
    返回值：pages_written 数值；读取失败时返回 0。
    逻辑：summary 不参与主流程控制，只做展示，因此异常时回退为 0。
    """

    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    try:
        return int(payload.get("pages_written") or 0)
    except (TypeError, ValueError):
        return 0


def filter_competitor_folder_items(payload: dict, parent_folder_id: str) -> list[dict]:
    """简介：按父文件夹 id 过滤竞争对手列表数据。
    参数：payload 为 folder-list 接口响应；parent_folder_id 为目标父文件夹 id。
    返回值：过滤后的 folder 项列表。
    逻辑：仅保留 parent_id 等于目标父文件夹 id 的子文件夹，忽略 root 和其他父节点。
    """

    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    filtered: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("parent_id") or "").strip() != parent_folder_id:
            continue
        filtered.append(item)
    return filtered


def build_filtered_folder_mapping_payload(config: CompetitorPatentPipelineConfig, filtered_items: list[dict]) -> dict:
    """简介：把过滤后的竞争对手列表包装成统一写盘结构。
    参数：config 为总流程配置；filtered_items 为过滤后的 folder 项。
    返回值：可直接写盘的标准化 payload。
    逻辑：保留 data 列表结构，兼容后续报表模块直接读取 folder_id -> folder_name 映射。
    """

    return {
        "status": True,
        "space_id": config.workspace_space_id,
        "parent_folder_id": config.competitor_parent_folder_id,
        "total": len(filtered_items),
        "data": filtered_items,
    }


def is_target_competitor_list_response(response, request_url: str) -> bool:
    return response.request.method.upper() == "GET" and response.url == request_url


async def ensure_pipeline_logged_in(managed, config: CompetitorPatentPipelineConfig) -> str:
    """简介：执行总流程第一步登录，并把 cookie 持久化到本地。
    参数：managed 为浏览器上下文包装对象；config 为总流程配置。
    返回值：登录完成后的页面 URL。
    逻辑：复用站点初始化模块，进入目标站点并等待登录成功态出现。
    """

    from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies
    from zhy.modules.site_init.initialize_site_async import initialize_site

    await load_cookies_if_present(managed.context, config.cookie_file)
    page = await initialize_site(
        context=managed.context,
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        timeout_seconds=config.login_timeout_seconds,
        poll_interval_seconds=config.login_poll_interval_seconds,
    )
    final_url = page.url
    await save_cookies(managed.context, config.cookie_file)
    await page.close()
    logger.info("[competitor_patent_pipeline] login complete: final_url={}", final_url)
    return final_url


async def fetch_competitor_folder_mapping(managed, config: CompetitorPatentPipelineConfig) -> tuple[Path, int]:
    """简介：进入竞争对手列表页面并截获 folder-list 响应，然后按父文件夹 id 过滤写盘。
    参数：managed 为浏览器上下文包装对象；config 为总流程配置。
    返回值：过滤后映射文件路径与保留条目数。
    逻辑：打开指定 workspace 页面，等待目标 GET 响应，保存原始快照与过滤结果。
    """

    page = await managed.context.new_page()
    try:
        async def open_target_page() -> None:
            await page.goto(
                config.competitor_list_page_url,
                wait_until="domcontentloaded",
                timeout=config.competitor_list_capture_timeout_ms,
            )

        try:
            async with page.expect_response(
                lambda response: is_target_competitor_list_response(response, config.competitor_list_request_url),
                timeout=config.competitor_list_capture_timeout_ms,
            ) as response_info:
                await open_target_page()
            response = await response_info.value
        except Exception:
            async with page.expect_response(
                lambda response: is_target_competitor_list_response(response, config.competitor_list_request_url),
                timeout=config.competitor_list_capture_timeout_ms,
            ) as response_info:
                await page.reload(wait_until="domcontentloaded", timeout=config.competitor_list_capture_timeout_ms)
            response = await response_info.value

        payload = await response.json()
        config.folder_mapping_raw_file.parent.mkdir(parents=True, exist_ok=True)
        config.folder_mapping_raw_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        filtered_items = filter_competitor_folder_items(payload, config.competitor_parent_folder_id)
        filtered_payload = build_filtered_folder_mapping_payload(config, filtered_items)
        save_json(config.folder_mapping_file, filtered_payload)
        logger.info(
            "[competitor_patent_pipeline] competitor list captured: total={} filtered={} output={}",
            len(payload.get("data", [])) if isinstance(payload, dict) and isinstance(payload.get("data"), list) else 0,
            len(filtered_items),
            config.folder_mapping_file,
        )
        return config.folder_mapping_file, len(filtered_items)
    finally:
        await page.close()


async def run_competitor_patent_pipeline(config: CompetitorPatentPipelineConfig) -> Path:
    """简介：执行竞争对手专利总流程的当前版本。
    参数：config 为总流程配置。
    返回值：本次运行 summary 文件路径。
    逻辑：当前先完成登录、竞争对手列表抓取和按月专利抓取，再写出 summary，后续步骤继续保留为 pending。
    """

    from playwright.async_api import async_playwright

    from zhy.modules.browser_context.browser_context_workflow import BrowserContextUserInput
    from zhy.modules.browser_context.runtime import build_browser_context

    browser_input = BrowserContextUserInput(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
    )
    summary_path = config.pipeline_output_dir / f"competitor_patent_pipeline_{config.month}_summary.json"

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=browser_input,
            headless=config.headless,
        )
        try:
            final_url = await ensure_pipeline_logged_in(managed, config)
            mapping_path, competitor_count = await fetch_competitor_folder_mapping(managed, config)
            monthly_summary_path, monthly_summary = await run_monthly_patent_fetch(
                config=config,
                managed=managed,
                folder_mapping_file=mapping_path,
            )
        finally:
            await managed.close()

    enrichment_summary_path = await run_existing_output_enrichment(
        build_existing_output_enrichment_config(config)
    )
    report_output_path = await asyncio.to_thread(
        run_competitor_patent_report,
        build_competitor_patent_report_config(config),
    )

    summary_payload = build_pipeline_summary_payload(
        config,
        login_status="done",
        login_final_url=final_url,
        competitor_list_status="done",
        competitor_list_count=competitor_count,
        competitor_list_output=str(mapping_path),
        monthly_patents_status="done",
        monthly_patents_folder_count=len(monthly_summary.get("folders", [])) if isinstance(monthly_summary, dict) else 0,
        monthly_patents_output=str(monthly_summary_path),
        enrich_patents_status="done",
        enrich_patents_output=str(enrichment_summary_path),
        enrich_patents_pages_written=load_enrichment_pages_written(enrichment_summary_path),
        build_monthly_report_status="done",
        build_monthly_report_output=str(report_output_path),
    )
    save_json(summary_path, summary_payload)
    logger.info("[competitor_patent_pipeline] summary written: {}", summary_path)
    return summary_path

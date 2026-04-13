from __future__ import annotations

from pathlib import Path

from loguru import logger
from playwright.async_api import async_playwright

from zhy.modules.browser_context.browser_context_workflow import BrowserContextUserInput
from zhy.modules.browser_context.runtime import build_browser_context
from zhy.modules.folder_patents_hybrid.abstract_fetch import build_abstract_headers
from zhy.modules.folder_patents_hybrid.api_fetch import RequestScheduler, fetch_folder_pages
from zhy.modules.folder_patents_hybrid.auth_capture import refresh_auth_state
from zhy.modules.folder_patents_hybrid.models import AuthRefreshRequiredError, FolderApiTarget, HybridTaskConfig
from zhy.modules.folder_patents_hybrid.storage import build_summary_path, load_auth_state_if_valid, save_json


async def run_folder_patents_hybrid(config: HybridTaskConfig, folder_targets: list[FolderApiTarget], default_space_id: str) -> Path:
    """
    简介：执行混合抓取主流程（文件夹串行、页码并发）。
    参数：config 为运行配置；folder_targets 为目标文件夹列表；default_space_id 用于命名 summary 文件。
    返回值：summary 文件路径。
    逻辑：初始化浏览器上下文 -> 逐个文件夹抓取 -> 自动刷新鉴权 -> 持续写入 run_summary。
    """

    if not folder_targets:
        raise ValueError("no folder targets resolved")
    if config.page_concurrency <= 0:
        raise ValueError("page_concurrency must be greater than 0")
    if config.size <= 0:
        raise ValueError("size must be greater than 0")

    output_root = Path(config.output_root)
    auth_state_path = Path(config.auth_state_file)
    summary_path = build_summary_path(output_root, default_space_id)

    run_summary = {
        "default_space_id": default_space_id,
        "folders": [],
    }
    save_json(summary_path, run_summary)

    scheduler = RequestScheduler(
        concurrency=config.page_concurrency,
        min_interval_seconds=config.min_request_interval_seconds,
        jitter_seconds=config.request_jitter_seconds,
    )
    proxies = {"http": config.proxy, "https": config.proxy} if config.proxy else None

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
            for target in folder_targets:
                try:
                    auth_state = load_auth_state_if_valid(auth_state_path, target.space_id, target.folder_id)

                    # 如果缓存鉴权不存在或不匹配，则先刷新一份新的鉴权参数。
                    if auth_state is None:
                        auth_state = await refresh_auth_state(managed, config, target.space_id, target.folder_id)

                    refresh_count = 0
                    while True:
                        headers = auth_state.to_headers(
                            origin=config.origin,
                            referer=config.referer,
                            user_agent=config.user_agent,
                            x_api_version=config.x_api_version,
                            x_patsnap_from=config.x_patsnap_from,
                            x_site_lang=config.x_site_lang,
                        )
                        abstract_headers = build_abstract_headers(
                            auth_state=auth_state,
                            origin=config.abstract_origin,
                            referer=config.abstract_referer,
                            user_agent=config.user_agent,
                            x_api_version=config.x_api_version,
                            x_patsnap_from=config.abstract_x_patsnap_from,
                            x_site_lang=config.x_site_lang,
                        )

                        try:
                            summary = await fetch_folder_pages(
                                space_id=target.space_id,
                                folder_id=target.folder_id,
                                auth_state=auth_state,
                                output_root=output_root,
                                start_page=config.start_page,
                                max_pages=config.max_pages,
                                page_concurrency=config.page_concurrency,
                                size=config.size,
                                timeout_seconds=config.timeout_seconds,
                                retry_count=config.retry_count,
                                retry_backoff_base_seconds=config.retry_backoff_base_seconds,
                                resume=config.resume,
                                scheduler=scheduler,
                                proxies=proxies,
                                headers=headers,
                                abstract_request_url=config.abstract_request_url,
                                abstract_request_template=config.abstract_request_template,
                                abstract_request_headers=abstract_headers,
                                abstract_text_field_name=config.abstract_text_field_name,
                            )
                            summary["auth_refresh_count"] = refresh_count
                            break
                        except AuthRefreshRequiredError as exc:
                            # 收到 401 时触发鉴权刷新，超过阈值后直接失败。
                            if refresh_count >= config.max_auth_refreshes:
                                raise RuntimeError("auth refresh retry limit reached") from exc
                            refresh_count += 1
                            auth_state = await refresh_auth_state(managed, config, target.space_id, target.folder_id)

                except Exception as exc:
                    summary = {
                        "space_id": target.space_id,
                        "folder_id": target.folder_id,
                        "status": "error",
                        "reason": "request_failed",
                        "total": None,
                        "limit": None,
                        "pages_saved": 0,
                        "last_page_requested": None,
                        "last_page_patent_count": None,
                        "saved_files": [],
                        "error": str(exc),
                        "auth_refresh_count": 0,
                        "abstract_failures": [],
                    }
                    logger.exception("[folder_patents_hybrid_workflow] folder failed: {}", target.folder_id)

                    run_summary["folders"].append(summary)
                    save_json(summary_path, run_summary)

                    # fail-fast 打开时，遇到文件夹失败立即退出循环。
                    if config.fail_fast:
                        break
                    continue

                run_summary["folders"].append(summary)
                save_json(summary_path, run_summary)
        finally:
            await managed.close()

    save_json(summary_path, run_summary)
    return summary_path

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table import FolderTableConfig, collect_folder_table, parse_folder_target
from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies
from zhy.modules.site_init.initialize_site_async import initialize_site


FOLDER_URLS = [
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=306f9f76aa5940a0acfc4b8a4dad8a18&page=1"
]
OUTPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_tables"
COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
CONCURRENCY = 3
START_PAGE = 1
PAGE_SIZE = 100
ZOOM_RATIO = 0.8
PAGE_TIMEOUT_MS = 30000
TABLE_READY_TIMEOUT_MS = 120000
SCROLL_STEP_PIXELS = 420
SCROLL_PAUSE_SECONDS = 0.5
MAX_STABLE_SCROLL_ROUNDS = 3
RETRY_COUNT = 3
RETRY_WAIT_SECONDS = 2.0
TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
SUCCESS_URL = TARGET_HOME_URL
SUCCESS_HEADER_SELECTOR = "#header-wrapper"
SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
GOTO_TIMEOUT_MS = 30000
LOGIN_TIMEOUT_SECONDS = 600.0
LOGIN_POLL_INTERVAL_SECONDS = 3.0
SELECTORS = {
    "table_container": ".excel-table-container",
    "table_scroll_container": ".excel-table-container .ht_master .wtHolder",
    "table_header_cells": ".excel-table-container .ht_master table.htCore thead th .colHeader",
    "table_row_selector": ".excel-table-container .ht_master table.htCore tbody tr",
    "page_size_trigger": ".pagination-size-select .el-input",
    "page_size_selected_text": ".pagination-size-select_popper .el-select-dropdown__item.selected span",
    "page_size_option_template": ".pagination-size-select_popper .el-select-dropdown__item:has-text('{size}')",
}


class QuickStartArgs:
    folder_urls = FOLDER_URLS
    concurrency = CONCURRENCY
    start_page = START_PAGE
    page_size = PAGE_SIZE
    zoom_ratio = ZOOM_RATIO
    page_timeout_ms = PAGE_TIMEOUT_MS
    table_ready_timeout_ms = TABLE_READY_TIMEOUT_MS
    scroll_step_pixels = SCROLL_STEP_PIXELS
    scroll_pause_seconds = SCROLL_PAUSE_SECONDS
    max_stable_scroll_rounds = MAX_STABLE_SCROLL_ROUNDS
    retry_count = RETRY_COUNT
    retry_wait_seconds = RETRY_WAIT_SECONDS
    output_root = OUTPUT_ROOT
    cookie_path = COOKIE_PATH


def main() -> None:
    async def run_quick_start() -> None:
        args = QuickStartArgs()
        config = FolderTableConfig(
            output_root_dir=args.output_root,
            concurrency=args.concurrency,
            start_page=args.start_page,
            expected_page_size=args.page_size,
            zoom_ratio=args.zoom_ratio,
            page_timeout_ms=args.page_timeout_ms,
            table_ready_timeout_ms=args.table_ready_timeout_ms,
            scroll_step_pixels=args.scroll_step_pixels,
            scroll_pause_seconds=args.scroll_pause_seconds,
            max_stable_scroll_rounds=args.max_stable_scroll_rounds,
            empty_page_wait_seconds=3.0,
            retry_count=args.retry_count,
            retry_wait_seconds=args.retry_wait_seconds,
        )

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            try:
                await load_cookies_if_present(context, args.cookie_path)
                login_page = await initialize_site(
                    context=context,
                    target_home_url=TARGET_HOME_URL,
                    success_url=SUCCESS_URL,
                    success_header_selector=SUCCESS_HEADER_SELECTOR,
                    success_logged_in_selector=SUCCESS_LOGGED_IN_SELECTOR,
                    success_content_selector=SUCCESS_CONTENT_SELECTOR,
                    loading_overlay_selector=LOADING_OVERLAY_SELECTOR,
                    goto_timeout_ms=GOTO_TIMEOUT_MS,
                    timeout_seconds=LOGIN_TIMEOUT_SECONDS,
                    poll_interval_seconds=LOGIN_POLL_INTERVAL_SECONDS,
                )
                await save_cookies(context, args.cookie_path)
                await login_page.close()

                for folder_url in args.folder_urls:
                    target = parse_folder_target(folder_url)
                    await collect_folder_table(
                        context=context,
                        target=target,
                        config=config,
                        selectors=SELECTORS,
                    )
            finally:
                await context.close()
                await browser.close()

    asyncio.run(run_quick_start())


if __name__ == "__main__":
    main()

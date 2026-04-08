import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from loguru import logger
from playwright.async_api import BrowserContext, Page, async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table import FolderTableConfig, collect_folder_table, parse_folder_target


DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
DEFAULT_GOTO_TIMEOUT_MS = 30000
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0

DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_tables"
DEFAULT_COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
DEFAULT_FOLDER_URLS = [
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=306f9f76aa5940a0acfc4b8a4dad8a18&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=7e56feab503f4c0fa5103f7e126a8aa0&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=7e80a0c91c024d378441f19a3abc5595&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=0b77a83bc2554d52b66e6350cb8729f3&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=55d9e6fa7c5b4cd6998e2209b386c8c6&page=1",

]
DEFAULT_CONCURRENCY = 3
DEFAULT_START_PAGE = 1
DEFAULT_PAGE_SIZE = 100
DEFAULT_ZOOM_RATIO = 0.8
DEFAULT_PAGE_TIMEOUT_MS = 30000
DEFAULT_TABLE_READY_TIMEOUT_MS = 120000
DEFAULT_SCROLL_STEP_PIXELS = 420
DEFAULT_SCROLL_PAUSE_SECONDS = 0.5
DEFAULT_MAX_STABLE_SCROLL_ROUNDS = 3
DEFAULT_EMPTY_PAGE_WAIT_SECONDS = 3.0
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_WAIT_SECONDS = 2.0

DEFAULT_SELECTORS = {
    "table_container": ".excel-table-container",
    "table_scroll_container": ".excel-table-container .ht_master .wtHolder",
    "table_header_cells": ".excel-table-container .ht_master table.htCore thead th .colHeader",
    "table_row_selector": ".excel-table-container .ht_master table.htCore tbody tr",
    "page_size_trigger": ".pagination-size-select .el-input",
    "page_size_selected_text": ".pagination-size-select_popper .el-select-dropdown__item.selected span",
    "page_size_option_template": ".pagination-size-select_popper .el-select-dropdown__item:has-text('{size}')",
}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect ZHY folder table data.")
    parser.add_argument("--folder-url", action="append", dest="folder_urls", default=[])
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--start-page", type=int, default=DEFAULT_START_PAGE)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--zoom-ratio", type=float, default=DEFAULT_ZOOM_RATIO)
    parser.add_argument("--page-timeout-ms", type=int, default=DEFAULT_PAGE_TIMEOUT_MS)
    parser.add_argument("--table-ready-timeout-ms", type=int, default=DEFAULT_TABLE_READY_TIMEOUT_MS)
    parser.add_argument("--scroll-step-pixels", type=int, default=DEFAULT_SCROLL_STEP_PIXELS)
    parser.add_argument("--scroll-pause-seconds", type=float, default=DEFAULT_SCROLL_PAUSE_SECONDS)
    parser.add_argument("--max-stable-scroll-rounds", type=int, default=DEFAULT_MAX_STABLE_SCROLL_ROUNDS)
    parser.add_argument("--retry-count", type=int, default=DEFAULT_RETRY_COUNT)
    parser.add_argument("--retry-wait-seconds", type=float, default=DEFAULT_RETRY_WAIT_SECONDS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT_DIR)
    parser.add_argument("--cookie-path", type=Path, default=DEFAULT_COOKIE_PATH)
    return parser


async def load_cookies_if_present(context: BrowserContext, cookie_path: Path) -> None:
    if not cookie_path.exists():
        return
    cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    if not cookies:
        return
    await context.add_cookies(cookies)
    logger.info("[folder_table_task] loaded {} cookies from {}", len(cookies), cookie_path)


async def save_cookies(context: BrowserContext, cookie_path: Path) -> None:
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookies = await context.cookies()
    cookie_path.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[folder_table_task] saved cookies to {}", cookie_path)


async def selector_exists(page: Page, selector: str) -> bool:
    return await page.locator(selector).count() > 0


async def selector_is_visible(page: Page, selector: str) -> bool:
    locator = page.locator(selector)
    if await locator.count() == 0:
        return False
    return await locator.first.is_visible()


async def has_reached_logged_in_state(
    page: Page,
    success_url: str,
    success_header_selector: str,
    success_logged_in_selector: str,
    success_content_selector: str,
    loading_overlay_selector: str,
) -> bool:
    if page.url.strip() != success_url:
        return False
    if not await selector_exists(page, success_header_selector):
        return False
    if not await selector_exists(page, success_logged_in_selector):
        return False
    if not await selector_exists(page, success_content_selector):
        return False
    if await selector_is_visible(page, loading_overlay_selector):
        return False
    return True


async def initialize_site(
    context: BrowserContext,
    target_home_url: str,
    success_url: str,
    success_header_selector: str,
    success_logged_in_selector: str,
    success_content_selector: str,
    loading_overlay_selector: str,
    goto_timeout_ms: int,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> Page:
    page = await context.new_page()
    try:
        await page.goto(target_home_url, wait_until="domcontentloaded", timeout=goto_timeout_ms)
    except Exception:
        logger.warning(
            "[folder_table_task] opening home page timed out, continue waiting for manual login"
        )

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if await has_reached_logged_in_state(
            page=page,
            success_url=success_url,
            success_header_selector=success_header_selector,
            success_logged_in_selector=success_logged_in_selector,
            success_content_selector=success_content_selector,
            loading_overlay_selector=loading_overlay_selector,
        ):
            logger.info("[folder_table_task] login success detected")
            return page
        logger.info(
            "[folder_table_task] login not ready yet, check again in {} seconds",
            poll_interval_seconds,
        )
        await page.wait_for_timeout(poll_interval_seconds * 1000)

    raise TimeoutError("waiting for manual login timed out")


async def run_task(args: argparse.Namespace) -> None:
    folder_urls = args.folder_urls or DEFAULT_FOLDER_URLS
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
        empty_page_wait_seconds=DEFAULT_EMPTY_PAGE_WAIT_SECONDS,
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
                target_home_url=DEFAULT_TARGET_HOME_URL,
                success_url=DEFAULT_SUCCESS_URL,
                success_header_selector=DEFAULT_SUCCESS_HEADER_SELECTOR,
                success_logged_in_selector=DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
                success_content_selector=DEFAULT_SUCCESS_CONTENT_SELECTOR,
                loading_overlay_selector=DEFAULT_LOADING_OVERLAY_SELECTOR,
                goto_timeout_ms=DEFAULT_GOTO_TIMEOUT_MS,
                timeout_seconds=DEFAULT_LOGIN_TIMEOUT_SECONDS,
                poll_interval_seconds=DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
            )
            await save_cookies(context, args.cookie_path)
            logger.info("[folder_table_task] site initialization finished at {}", login_page.url)

            for folder_url in folder_urls:
                target = parse_folder_target(folder_url)
                result = await collect_folder_table(
                    context=context,
                    target=target,
                    config=config,
                    selectors=DEFAULT_SELECTORS,
                )
                logger.info(
                    "[folder_table_task] folder {} finished: {} pages, {} rows",
                    result.folder_id,
                    result.total_pages_collected,
                    result.total_rows_collected,
                )
        finally:
            await context.close()
            await browser.close()


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    asyncio.run(run_task(args))


if __name__ == "__main__":
    main()

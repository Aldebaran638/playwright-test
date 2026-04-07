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
from zhy.modules.site_init.initialize_site import (
    DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
    DEFAULT_LOGIN_TIMEOUT_SECONDS,
    LOADING_OVERLAY_SELECTOR,
    SUCCESS_CONTENT_SELECTOR,
    SUCCESS_HEADER_SELECTOR,
    SUCCESS_LOGGED_IN_SELECTOR,
    TARGET_HOME_URL,
)


DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_tables"
DEFAULT_COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
DEFAULT_FOLDER_URLS = [
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=306f9f76aa5940a0acfc4b8a4dad8a18&page=1"
]
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
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--zoom-ratio", type=float, default=0.8)
    parser.add_argument("--page-timeout-ms", type=int, default=30000)
    parser.add_argument("--table-ready-timeout-ms", type=int, default=15000)
    parser.add_argument("--scroll-step-pixels", type=int, default=420)
    parser.add_argument("--scroll-pause-seconds", type=float, default=0.5)
    parser.add_argument("--max-stable-scroll-rounds", type=int, default=3)
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


async def has_reached_logged_in_state(page: Page) -> bool:
    if page.url.strip() != TARGET_HOME_URL:
        return False
    if not await selector_exists(page, SUCCESS_HEADER_SELECTOR):
        return False
    if not await selector_exists(page, SUCCESS_LOGGED_IN_SELECTOR):
        return False
    if not await selector_exists(page, SUCCESS_CONTENT_SELECTOR):
        return False
    if await selector_is_visible(page, LOADING_OVERLAY_SELECTOR):
        return False
    return True


async def initialize_site(context: BrowserContext) -> Page:
    page = await context.new_page()
    try:
        await page.goto(TARGET_HOME_URL, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        logger.warning(
            "[folder_table_task] opening home page timed out, continue waiting for manual login"
        )

    deadline = time.time() + DEFAULT_LOGIN_TIMEOUT_SECONDS
    while time.time() < deadline:
        if await has_reached_logged_in_state(page):
            logger.info("[folder_table_task] login success detected")
            return page
        logger.info(
            "[folder_table_task] login not ready yet, check again in {} seconds",
            DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
        )
        await page.wait_for_timeout(DEFAULT_LOGIN_POLL_INTERVAL_SECONDS * 1000)

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
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()

        try:
            await load_cookies_if_present(context, args.cookie_path)
            login_page = await initialize_site(context)
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

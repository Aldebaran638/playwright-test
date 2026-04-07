import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.browser_context.browser_context_cli import (
    collect_browser_context_user_input,
    display_browser_context_workflow_result,
)
from zhy.modules.browser_context.browser_context_probe import probe_browser_context_mode
from zhy.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    BrowserEnvMode,
    resolve_browser_context_mode,
)
from zhy.modules.folder_table import FolderTableConfig, collect_folder_table, parse_folder_target
from zhy.tasks.folder_table_collect_task import (
    DEFAULT_COOKIE_PATH,
    DEFAULT_FOLDER_URLS,
    DEFAULT_OUTPUT_ROOT_DIR,
    DEFAULT_SELECTORS,
    initialize_site,
    load_cookies_if_present,
    save_cookies,
)


@dataclass
class ManagedBrowserContext:
    context: BrowserContext
    browser: Browser | None
    workflow_result: BrowserContextWorkflowResult

    def is_persistent(self) -> bool:
        return self.browser is None

    async def close(self) -> None:
        await self.context.close()
        if self.browser is not None:
            await self.browser.close()


async def launch_context_for_mode(
    playwright: Playwright,
    mode: BrowserEnvMode,
    user_input: BrowserContextUserInput,
    headless: bool,
) -> tuple[BrowserContext, Browser | None]:
    chromium = playwright.chromium

    if mode == "full_persistent":
        context = await chromium.launch_persistent_context(
            user_data_dir=user_input.user_data_dir or "",
            executable_path=user_input.browser_executable_path,
            headless=headless,
        )
        return context, None

    if mode == "custom_browser_ephemeral":
        browser = await chromium.launch(
            executable_path=user_input.browser_executable_path,
            headless=headless,
        )
        return await browser.new_context(), browser

    if mode == "default_browser_persistent":
        context = await chromium.launch_persistent_context(
            user_data_dir=user_input.user_data_dir or "",
            headless=headless,
        )
        return context, None

    browser = await chromium.launch(headless=headless)
    return await browser.new_context(), browser


async def build_browser_context(
    playwright: Playwright,
    user_input: BrowserContextUserInput,
    headless: bool,
) -> ManagedBrowserContext:
    workflow_result = resolve_browser_context_mode(user_input, probe_browser_context_mode)
    display_browser_context_workflow_result(workflow_result)
    if not workflow_result.success or workflow_result.resolved_mode is None:
        raise RuntimeError("failed to resolve a usable browser context mode")

    normalized = user_input.normalized()
    context, browser = await launch_context_for_mode(
        playwright=playwright,
        mode=workflow_result.resolved_mode,
        user_input=normalized,
        headless=headless,
    )
    return ManagedBrowserContext(
        context=context,
        browser=browser,
        workflow_result=workflow_result,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full ZHY pipeline.")
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
    parser.add_argument("--headless", action="store_true")
    return parser


async def run_pipeline(args: argparse.Namespace) -> None:
    folder_urls = args.folder_urls or DEFAULT_FOLDER_URLS
    folder_targets = [parse_folder_target(url) for url in folder_urls]
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

    user_input = collect_browser_context_user_input()

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=user_input,
            headless=args.headless,
        )

        try:
            await load_cookies_if_present(managed.context, args.cookie_path)
            login_page = await initialize_site(managed.context)
            await save_cookies(managed.context, args.cookie_path)
            logger.info("[zhy_total_pipeline] site initialization finished at {}", login_page.url)

            for target in folder_targets:
                result = await collect_folder_table(
                    context=managed.context,
                    target=target,
                    config=config,
                    selectors=DEFAULT_SELECTORS,
                )
                logger.info(
                    "[zhy_total_pipeline] folder {} finished: {} pages, {} rows",
                    result.folder_id,
                    result.total_pages_collected,
                    result.total_rows_collected,
                )
        finally:
            await managed.close()


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()

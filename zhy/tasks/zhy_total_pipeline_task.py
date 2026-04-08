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
    DEFAULT_GOTO_TIMEOUT_MS,
    DEFAULT_LOADING_OVERLAY_SELECTOR,
    DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
    DEFAULT_LOGIN_TIMEOUT_SECONDS,
    DEFAULT_OUTPUT_ROOT_DIR,
    DEFAULT_SELECTORS,
    DEFAULT_SUCCESS_CONTENT_SELECTOR,
    DEFAULT_SUCCESS_HEADER_SELECTOR,
    DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
    DEFAULT_SUCCESS_URL,
    DEFAULT_TARGET_HOME_URL,
    initialize_site,
    load_cookies_if_present,
    save_cookies,
)


DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
DEFAULT_FOLDER_CONCURRENCY = 1
DEFAULT_CONCURRENCY = 1
DEFAULT_START_PAGE = 1
DEFAULT_PAGE_SIZE = 100
DEFAULT_ZOOM_RATIO = 0.8
DEFAULT_PAGE_TIMEOUT_MS = 30000
DEFAULT_TABLE_READY_TIMEOUT_MS = 120000
DEFAULT_SCROLL_STEP_PIXELS = 420
DEFAULT_SCROLL_PAUSE_SECONDS = 0.5
DEFAULT_MAX_STABLE_SCROLL_ROUNDS = 3
DEFAULT_EMPTY_PAGE_WAIT_SECONDS = 6.0
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_WAIT_SECONDS = 2.0
DEFAULT_HEADLESS = False


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


def build_default_browser_context_user_input() -> BrowserContextUserInput:
    # 统一收口总流程文件里的浏览器上下文默认值。
    return BrowserContextUserInput(
        browser_executable_path=DEFAULT_BROWSER_EXECUTABLE_PATH,
        user_data_dir=DEFAULT_USER_DATA_DIR,
    )


def merge_browser_context_user_input(
    user_input: BrowserContextUserInput,
    default_input: BrowserContextUserInput,
) -> BrowserContextUserInput:
    # 用户没有输入时回落到总流程文件中硬编码的默认值。
    normalized_user_input = user_input.normalized()
    normalized_default_input = default_input.normalized()
    return BrowserContextUserInput(
        browser_executable_path=(
            normalized_user_input.browser_executable_path
            or normalized_default_input.browser_executable_path
        ),
        user_data_dir=(
            normalized_user_input.user_data_dir
            or normalized_default_input.user_data_dir
        ),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full ZHY pipeline.")
    parser.add_argument("--folder-url", action="append", dest="folder_urls", default=[])
    parser.add_argument("--folder-concurrency", type=int, default=DEFAULT_FOLDER_CONCURRENCY)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--start-page", type=int, default=DEFAULT_START_PAGE)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--zoom-ratio", type=float, default=DEFAULT_ZOOM_RATIO)
    parser.add_argument("--page-timeout-ms", type=int, default=DEFAULT_PAGE_TIMEOUT_MS)
    parser.add_argument(
        "--table-ready-timeout-ms",
        type=int,
        default=DEFAULT_TABLE_READY_TIMEOUT_MS,
    )
    parser.add_argument("--scroll-step-pixels", type=int, default=DEFAULT_SCROLL_STEP_PIXELS)
    parser.add_argument("--scroll-pause-seconds", type=float, default=DEFAULT_SCROLL_PAUSE_SECONDS)
    parser.add_argument(
        "--max-stable-scroll-rounds",
        type=int,
        default=DEFAULT_MAX_STABLE_SCROLL_ROUNDS,
    )
    parser.add_argument("--retry-count", type=int, default=DEFAULT_RETRY_COUNT)
    parser.add_argument("--retry-wait-seconds", type=float, default=DEFAULT_RETRY_WAIT_SECONDS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT_DIR)
    parser.add_argument("--cookie-path", type=Path, default=DEFAULT_COOKIE_PATH)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    return parser


async def collect_single_folder(
    context: BrowserContext,
    target,
    config: FolderTableConfig,
    selectors: dict[str, str],
):
    # 单独包装单个文件夹抓取，方便总流程在文件夹级别做并发调度。
    return await collect_folder_table(
        context=context,
        target=target,
        config=config,
        selectors=selectors,
    )


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
        empty_page_wait_seconds=DEFAULT_EMPTY_PAGE_WAIT_SECONDS,
        retry_count=args.retry_count,
        retry_wait_seconds=args.retry_wait_seconds,
    )

    default_browser_context_input = build_default_browser_context_user_input()
    collected_user_input = collect_browser_context_user_input()
    user_input = merge_browser_context_user_input(
        collected_user_input,
        default_browser_context_input,
    )

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=user_input,
            headless=args.headless,
        )

        try:
            await load_cookies_if_present(managed.context, args.cookie_path)
            login_page = await initialize_site(
                context=managed.context,
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
            await save_cookies(managed.context, args.cookie_path)
            logger.info("[zhy_total_pipeline] site initialization finished at {}", login_page.url)

            folder_semaphore = asyncio.Semaphore(max(args.folder_concurrency, 1))

            async def run_folder_with_limit(target):
                # 限制同时运行的文件夹数量，避免一次开过多标签页。
                async with folder_semaphore:
                    return await collect_single_folder(
                        context=managed.context,
                        target=target,
                        config=config,
                        selectors=DEFAULT_SELECTORS,
                    )

            folder_tasks = [
                asyncio.create_task(run_folder_with_limit(target))
                for target in folder_targets
            ]

            for result in await asyncio.gather(*folder_tasks):
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

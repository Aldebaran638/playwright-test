import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger
from playwright.async_api import async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.browser_context.browser_context_workflow import BrowserContextUserInput
from zhy.modules.browser_context.runtime import build_browser_context
from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies
from zhy.modules.folder_table.page_url import parse_folder_target
from zhy.modules.folder_table_probe import (
    FolderTableProbeConfig,
    RecentPatentPublication,
    build_page_numbers,
    probe_folder_pages,
    write_recent_publication_numbers,
)
from zhy.modules.site_init.initialize_site_async import initialize_site


# 浏览器可执行文件默认路径，默认模式下直接复用该浏览器环境。
DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# 浏览器用户数据目录默认路径，默认模式下直接沿用现有登录态。
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
# 站点初始化首页地址。
DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
# 登录成功后应到达的 URL。
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
# 登录成功头部标记选择器。
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
# 登录成功头像标记选择器。
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
# 登录成功主内容标记选择器。
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
# 预加载遮罩选择器。
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
# 首页打开超时毫秒数。
DEFAULT_GOTO_TIMEOUT_MS = 30000
# 最长等待登录成功秒数。
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
# 登录轮询间隔秒数。
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0
# 默认 Cookie 文件路径。
DEFAULT_COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
# 默认探测输出根目录。
DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_table_probe"
# 默认待处理文件夹 URL 列表。
DEFAULT_FOLDER_URLS = [
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=306f9f76aa5940a0acfc4b8a4dad8a18&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=7e56feab503f4c0fa5103f7e126a8aa0&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=7e80a0c91c024d378441f19a3abc5595&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=0b77a83bc2554d52b66e6350cb8729f3&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=55d9e6fa7c5b4cd6998e2209b386c8c6&page=1",
]
# 默认单页模式页码。
DEFAULT_PAGE_NUMBER = 3
# 默认单文件夹页级并发数。
DEFAULT_PAGE_CONCURRENCY = 5
# 默认表格每页条数，优先固定为 20 提高稳定性。
DEFAULT_PAGE_SIZE = 20
# 默认单页打开超时毫秒数。
DEFAULT_PAGE_TIMEOUT_MS = 30000
# 默认表格壳层可见等待超时毫秒数。
DEFAULT_TABLE_READY_TIMEOUT_MS = 120000
# 默认字段和行缓冲等待秒数。
DEFAULT_BUFFER_WAIT_SECONDS = 6.0
# 默认单次滚动像素。
DEFAULT_SCROLL_STEP_PIXELS = 420
# 默认滚动暂停秒数。
DEFAULT_SCROLL_PAUSE_SECONDS = 0.5
# 默认连续多少轮稳定后判定滚到底。
DEFAULT_MAX_STABLE_SCROLL_ROUNDS = 3
# 默认是否无头。
DEFAULT_HEADLESS = False
# 默认是否强制使用整套默认参数，1 表示强制默认值，0 表示按命令行参数执行。
DEFAULT_USE_DEFAULTS = 1
# 当前表格选择器定义，模块层统一通过参数接收，避免在模块内部硬编码。
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
    parser = argparse.ArgumentParser(description="Probe ZHY folder tables with serial folders and concurrent pages.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--folder-url", action="append", dest="folder_urls", default=[])
    parser.add_argument("--page-number", type=int, default=DEFAULT_PAGE_NUMBER)
    parser.add_argument("--start-page", type=int)
    parser.add_argument("--end-page", type=int)
    parser.add_argument("--page-concurrency", type=int, default=DEFAULT_PAGE_CONCURRENCY)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--cookie-path", type=Path, default=DEFAULT_COOKIE_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT_DIR)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    parser.add_argument("--page-timeout-ms", type=int, default=DEFAULT_PAGE_TIMEOUT_MS)
    parser.add_argument("--table-ready-timeout-ms", type=int, default=DEFAULT_TABLE_READY_TIMEOUT_MS)
    parser.add_argument("--buffer-wait-seconds", type=float, default=DEFAULT_BUFFER_WAIT_SECONDS)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--scroll-step-pixels", type=int, default=DEFAULT_SCROLL_STEP_PIXELS)
    parser.add_argument("--scroll-pause-seconds", type=float, default=DEFAULT_SCROLL_PAUSE_SECONDS)
    parser.add_argument("--max-stable-scroll-rounds", type=int, default=DEFAULT_MAX_STABLE_SCROLL_ROUNDS)
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    # 当 use-defaults=0 时，保留命令行传入值，直接按当前参数执行。
    if args.use_defaults == 0:
        return args

    # 当 use-defaults=1 时，统一回落到当前文件维护的默认值，方便开发者直接运行。
    args.folder_urls = list(DEFAULT_FOLDER_URLS)
    args.page_number = DEFAULT_PAGE_NUMBER
    args.start_page = None
    args.end_page = None
    args.page_concurrency = DEFAULT_PAGE_CONCURRENCY
    args.browser_executable_path = DEFAULT_BROWSER_EXECUTABLE_PATH
    args.user_data_dir = DEFAULT_USER_DATA_DIR
    args.cookie_path = DEFAULT_COOKIE_PATH
    args.output_root = DEFAULT_OUTPUT_ROOT_DIR
    args.headless = DEFAULT_HEADLESS
    args.page_timeout_ms = DEFAULT_PAGE_TIMEOUT_MS
    args.table_ready_timeout_ms = DEFAULT_TABLE_READY_TIMEOUT_MS
    args.buffer_wait_seconds = DEFAULT_BUFFER_WAIT_SECONDS
    args.page_size = DEFAULT_PAGE_SIZE
    args.scroll_step_pixels = DEFAULT_SCROLL_STEP_PIXELS
    args.scroll_pause_seconds = DEFAULT_SCROLL_PAUSE_SECONDS
    args.max_stable_scroll_rounds = DEFAULT_MAX_STABLE_SCROLL_ROUNDS
    return args


def build_browser_context_user_input(args: argparse.Namespace) -> BrowserContextUserInput:
    return BrowserContextUserInput(
        browser_executable_path=args.browser_executable_path,
        user_data_dir=args.user_data_dir,
    )


def build_folder_probe_config(args: argparse.Namespace) -> FolderTableProbeConfig:
    return FolderTableProbeConfig(
        output_root_dir=args.output_root,
        page_numbers=build_page_numbers(args.page_number, args.start_page, args.end_page),
        page_concurrency=args.page_concurrency,
        page_size=args.page_size,
        page_timeout_ms=args.page_timeout_ms,
        table_ready_timeout_ms=args.table_ready_timeout_ms,
        buffer_wait_seconds=args.buffer_wait_seconds,
        scroll_step_pixels=args.scroll_step_pixels,
        scroll_pause_seconds=args.scroll_pause_seconds,
        max_stable_scroll_rounds=args.max_stable_scroll_rounds,
    )


# 简介：执行 folder_table_probe 总流程。
# 参数：
# - args: 命令行解析后的参数对象。
# 返回值：
# - 无返回值。
# 逻辑：
# - 先创建浏览器上下文并完成站点初始化，再按“文件夹串行、页码并发”的策略逐个处理文件夹。
async def run_probe(args: argparse.Namespace) -> None:
    runtime_args = apply_default_mode(args)
    folder_urls = runtime_args.folder_urls or list(DEFAULT_FOLDER_URLS)
    probe_config = build_folder_probe_config(runtime_args)
    browser_context_user_input = build_browser_context_user_input(runtime_args)
    matched_recent_publications: list[RecentPatentPublication] = []

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=browser_context_user_input,
            headless=runtime_args.headless,
        )

        try:
            # 先加载已有 Cookie，尽量避免重复登录。
            await load_cookies_if_present(managed.context, runtime_args.cookie_path)

            # 当前步骤负责把站点初始化到可进入文件夹表格的状态。
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
            await save_cookies(managed.context, runtime_args.cookie_path)
            logger.info("[folder_table_probe_task] site initialization finished at {}", login_page.url)

            # 文件夹之间严格串行执行，避免多个文件夹并发争抢同一浏览器上下文。
            for folder_url in folder_urls:
                target = parse_folder_target(folder_url)

                # 当前循环只处理一个文件夹，文件夹内部的页码并发交给模块层控制。
                summary = await probe_folder_pages(
                    context=managed.context,
                    target=target,
                    config=probe_config,
                    selectors=DEFAULT_SELECTORS,
                )
                matched_recent_publications.extend(summary.recent_publications)
                recent_publication_output_path = write_recent_publication_numbers(
                    output_root_dir=runtime_args.output_root,
                    matched_records=matched_recent_publications,
                )
                logger.info(
                    "[folder_table_probe_task] folder {} finished: successful_pages={} failed_pages={} total_rows_written={} recent_publications={} output_dir={} recent_output={}",
                    summary.folder_id,
                    summary.successful_pages,
                    summary.failed_pages,
                    summary.total_rows_written,
                    len(summary.recent_publications),
                    summary.output_dir,
                    recent_publication_output_path,
                )
        finally:
            await managed.close()


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    asyncio.run(run_probe(args))


if __name__ == "__main__":
    main()
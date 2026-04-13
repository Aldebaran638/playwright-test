import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.browser.build_context import build_browser_context
from zhy.modules.browser.context_config import BrowserContextUserInput
from zhy.modules.common.run_step import run_step_async
from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError, FolderApiTarget, HybridTaskConfig
from zhy.modules.fetch.folder_patents_abstract import build_abstract_headers
from zhy.modules.fetch.folder_patents_api import RequestScheduler, fetch_folder_pages
from zhy.modules.fetch.folder_patents_auth import refresh_auth_state
from zhy.modules.persist.auth_state_io import load_auth_state_if_valid
from zhy.modules.persist.json_io import save_json
from zhy.modules.persist.page_path import build_patents_summary_path


# 默认浏览器可执行文件路径。
DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# 默认用户数据目录。
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
# 默认 Cookie 文件路径。
DEFAULT_COOKIE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
# 默认鉴权缓存文件路径。
DEFAULT_AUTH_STATE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "folder_patents_auth.json"
# 默认输出根目录。
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"
# 默认起始页。
DEFAULT_START_PAGE = 1
# 默认最大页数；None 表示不限。
DEFAULT_MAX_PAGES: int | None = None
# 默认页面并发数。
DEFAULT_PAGE_CONCURRENCY = 5
# 默认每页条数。
DEFAULT_SIZE = 100
# 默认请求超时（秒）。
DEFAULT_TIMEOUT_SECONDS = 30.0
# 默认鉴权截获超时（毫秒）。
DEFAULT_CAPTURE_TIMEOUT_MS = 45000
# 默认最大鉴权刷新次数。
DEFAULT_MAX_AUTH_REFRESHES = 5
# 默认请求重试次数。
DEFAULT_RETRY_COUNT = 3
# 默认重试回退基数（秒）。
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 1.0
# 默认最小请求间隔（秒）。
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.2
# 默认请求抖动上限（秒）。
DEFAULT_REQUEST_JITTER_SECONDS = 0.4
# 默认代理。
DEFAULT_PROXY: str | None = None
# 默认是否跳过已生成的页文件。
DEFAULT_RESUME = True
# 默认是否无头运行浏览器。
DEFAULT_HEADLESS = False
# 默认是否遇到第一个文件夹失败就退出。
DEFAULT_FAIL_FAST = False

# 默认请求头参数。
DEFAULT_ORIGIN = "https://workspace.zhihuiya.com"
DEFAULT_REFERER = "https://workspace.zhihuiya.com/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)
DEFAULT_X_API_VERSION = "2.0"
DEFAULT_X_PATSNAP_FROM = "w-analytics-workspace"
DEFAULT_X_SITE_LANG = "CN"

# 默认摘要接口请求头参数。
DEFAULT_ABSTRACT_ORIGIN = "https://analytics.zhihuiya.com"
DEFAULT_ABSTRACT_REFERER = "https://analytics.zhihuiya.com/"
DEFAULT_ABSTRACT_X_PATSNAP_FROM = "w-analytics-patent-view"
DEFAULT_ABSTRACT_REQUEST_URL = "https://search-service.zhihuiya.com/core-search-api/search/translate/patent"
DEFAULT_ABSTRACT_TEXT_FIELD_NAME = "ABST"
DEFAULT_ABSTRACT_REQUEST_TEMPLATE: dict = {
    "highlight": True,
    "lang": "CN",
    "original": False,
    "field": "ABST",
    "source_type": "workspace",
    "view_type": "workspace",
    "bio_uk": "",
    "uk": "undefined",
    "ws_view_type": "tablelist",
    "page": 1,
    "_type": "workspace",
    "sort": "wtasc",
    "rows": "20",
    "qid": "",
    "efqid": "",
    "cond": "",
    "product": "Analytics",
    "path": "",
    "signature": "SlyJYZh8rcYm7FkbmyfSEbN7DmQefitqdIkhrtBXiFM=",
    "shareFrom": "VIEW",
    "date": "20260310T034642Z",
    "expire": "94608000",
    "shareId": "FGBB71D62FEF8EF82F7238F08BF528EC",
    "version": "1.0",
}

# 站点初始化参数。
DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
DEFAULT_GOTO_TIMEOUT_MS = 30000
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0

# 默认文件夹目标列表（space_id, folder_id 组合），测试时可按需修改。
DEFAULT_FOLDER_TARGETS: list[tuple[str, str]] = [
    # ("space_id", "folder_id"),
]
# 默认 space_id，用于 summary 文件命名。
DEFAULT_SPACE_ID = "ccb6031b05034c7ab2c4b120c2dc3155"

# 是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_config_from_args(args: argparse.Namespace) -> HybridTaskConfig:
    """简介：把命令行参数转换为混合抓取配置对象。
    参数：args 为命令行参数对象。
    返回值：HybridTaskConfig。
    """
    return HybridTaskConfig(
        browser_executable_path=args.browser_executable_path,
        user_data_dir=args.user_data_dir,
        cookie_file=args.cookie_file,
        auth_state_file=args.auth_state_file,
        output_root=str(args.output_root),
        target_home_url=DEFAULT_TARGET_HOME_URL,
        success_url=DEFAULT_SUCCESS_URL,
        success_header_selector=DEFAULT_SUCCESS_HEADER_SELECTOR,
        success_logged_in_selector=DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
        success_content_selector=DEFAULT_SUCCESS_CONTENT_SELECTOR,
        loading_overlay_selector=DEFAULT_LOADING_OVERLAY_SELECTOR,
        goto_timeout_ms=DEFAULT_GOTO_TIMEOUT_MS,
        login_timeout_seconds=DEFAULT_LOGIN_TIMEOUT_SECONDS,
        login_poll_interval_seconds=DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
        origin=DEFAULT_ORIGIN,
        referer=DEFAULT_REFERER,
        user_agent=DEFAULT_USER_AGENT,
        x_api_version=DEFAULT_X_API_VERSION,
        x_patsnap_from=DEFAULT_X_PATSNAP_FROM,
        x_site_lang=DEFAULT_X_SITE_LANG,
        abstract_request_url=DEFAULT_ABSTRACT_REQUEST_URL,
        abstract_origin=DEFAULT_ABSTRACT_ORIGIN,
        abstract_referer=DEFAULT_ABSTRACT_REFERER,
        abstract_x_patsnap_from=DEFAULT_ABSTRACT_X_PATSNAP_FROM,
        abstract_request_template=DEFAULT_ABSTRACT_REQUEST_TEMPLATE,
        abstract_text_field_name=DEFAULT_ABSTRACT_TEXT_FIELD_NAME,
        start_page=args.start_page,
        max_pages=args.max_pages,
        page_concurrency=args.page_concurrency,
        size=args.size,
        timeout_seconds=args.timeout_seconds,
        capture_timeout_ms=args.capture_timeout_ms,
        max_auth_refreshes=args.max_auth_refreshes,
        retry_count=args.retry_count,
        retry_backoff_base_seconds=args.retry_backoff_base_seconds,
        min_request_interval_seconds=args.min_request_interval_seconds,
        request_jitter_seconds=args.request_jitter_seconds,
        resume=args.resume,
        proxy=args.proxy,
        headless=args.headless,
        fail_fast=args.fail_fast,
    )


async def run_folder_patents_hybrid(config: HybridTaskConfig, folder_targets: list[FolderApiTarget], default_space_id: str) -> Path:
    """简介：执行混合抓取主流程（文件夹串行、页码并发）。
    参数：config 为运行配置；folder_targets 为目标文件夹列表；default_space_id 用于命名 summary 文件。
    返回值：summary 文件路径。
    逻辑：初始化浏览器上下文 -> 逐个文件夹抓取 -> 自动刷新鉴权 -> 持续写入 run_summary。
    """
    from playwright.async_api import async_playwright

    if not folder_targets:
        raise ValueError("no folder targets resolved")
    if config.page_concurrency <= 0:
        raise ValueError("page_concurrency must be greater than 0")
    if config.size <= 0:
        raise ValueError("size must be greater than 0")

    output_root = Path(config.output_root)
    auth_state_path = Path(config.auth_state_file)
    summary_path = build_patents_summary_path(output_root, default_space_id)

    run_summary: dict = {
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
                    logger.exception("[folder_patents_hybrid_task] folder failed: {}", target.folder_id)
                    run_summary["folders"].append(summary)
                    save_json(summary_path, run_summary)
                    if config.fail_fast:
                        break
                    continue

                run_summary["folders"].append(summary)
                save_json(summary_path, run_summary)
        finally:
            await managed.close()

    save_json(summary_path, run_summary)
    return summary_path


def build_argument_parser() -> argparse.ArgumentParser:
    """简介：构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Run folder patents hybrid fetch task.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_FILE)
    parser.add_argument("--auth-state-file", type=Path, default=DEFAULT_AUTH_STATE_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--start-page", type=int, default=DEFAULT_START_PAGE)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--page-concurrency", type=int, default=DEFAULT_PAGE_CONCURRENCY)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--capture-timeout-ms", type=int, default=DEFAULT_CAPTURE_TIMEOUT_MS)
    parser.add_argument("--max-auth-refreshes", type=int, default=DEFAULT_MAX_AUTH_REFRESHES)
    parser.add_argument("--retry-count", type=int, default=DEFAULT_RETRY_COUNT)
    parser.add_argument("--retry-backoff-base-seconds", type=float, default=DEFAULT_RETRY_BACKOFF_BASE_SECONDS)
    parser.add_argument("--min-request-interval-seconds", type=float, default=DEFAULT_MIN_REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--request-jitter-seconds", type=float, default=DEFAULT_REQUEST_JITTER_SECONDS)
    parser.add_argument("--proxy", default=DEFAULT_PROXY)
    parser.add_argument("--resume", action="store_true", default=DEFAULT_RESUME)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    parser.add_argument("--fail-fast", action="store_true", default=DEFAULT_FAIL_FAST)
    parser.add_argument("--space-id", default=DEFAULT_SPACE_ID)
    parser.add_argument(
        "--folder",
        action="append",
        nargs=2,
        metavar=("SPACE_ID", "FOLDER_ID"),
        dest="folder_args",
        default=[],
    )
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    if args.use_defaults == 0:
        return args
    args.browser_executable_path = DEFAULT_BROWSER_EXECUTABLE_PATH
    args.user_data_dir = DEFAULT_USER_DATA_DIR
    args.cookie_file = DEFAULT_COOKIE_FILE
    args.auth_state_file = DEFAULT_AUTH_STATE_FILE
    args.output_root = DEFAULT_OUTPUT_ROOT
    args.start_page = DEFAULT_START_PAGE
    args.max_pages = DEFAULT_MAX_PAGES
    args.page_concurrency = DEFAULT_PAGE_CONCURRENCY
    args.size = DEFAULT_SIZE
    args.timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    args.capture_timeout_ms = DEFAULT_CAPTURE_TIMEOUT_MS
    args.max_auth_refreshes = DEFAULT_MAX_AUTH_REFRESHES
    args.retry_count = DEFAULT_RETRY_COUNT
    args.retry_backoff_base_seconds = DEFAULT_RETRY_BACKOFF_BASE_SECONDS
    args.min_request_interval_seconds = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS
    args.request_jitter_seconds = DEFAULT_REQUEST_JITTER_SECONDS
    args.proxy = DEFAULT_PROXY
    args.resume = DEFAULT_RESUME
    args.headless = DEFAULT_HEADLESS
    args.fail_fast = DEFAULT_FAIL_FAST
    args.space_id = DEFAULT_SPACE_ID
    args.folder_args = [(s, f) for s, f in DEFAULT_FOLDER_TARGETS]
    return args


async def run_task(args: argparse.Namespace) -> Path:
    """简介：执行文件夹专利混合抓取 task。
    参数：args 为已解析的流程参数。
    返回值：本次运行 summary 文件路径。
    逻辑：解析目标文件夹 -> 构建配置 -> 调用混合抓取主流程。
    """
    folder_targets = [
        FolderApiTarget(space_id=space_id, folder_id=folder_id)
        for space_id, folder_id in (args.folder_args or [])
    ]
    if not folder_targets:
        for space_id, folder_id in DEFAULT_FOLDER_TARGETS:
            folder_targets.append(FolderApiTarget(space_id=space_id, folder_id=folder_id))

    config = build_config_from_args(args)

    step = await run_step_async(
        run_folder_patents_hybrid,
        config,
        folder_targets,
        args.space_id,
        step_name="执行文件夹专利混合抓取",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    summary_path = step.value
    if summary_path is None:
        raise RuntimeError("folder patents hybrid task did not return a summary path")
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    summary_path = asyncio.run(run_task(args))
    logger.info("[folder_patents_hybrid_task] done: summary={}", summary_path)


if __name__ == "__main__":
    main()

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
from zhy.modules.common.types.enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError, FolderAuthState, HybridTaskConfig
from zhy.modules.fetch.folder_patents_abstract import build_abstract_headers
from zhy.modules.fetch.folder_patents_api import RequestScheduler
from zhy.modules.fetch.folder_patents_auth import refresh_auth_state
from zhy.modules.fetch.patent_basic import build_page_supplement_payload
from zhy.modules.persist.auth_state_io import load_auth_state_from_file
from zhy.modules.persist.json_io import load_json_file_any_utf, save_json
from zhy.modules.persist.page_path import build_enrichment_page_path, iter_input_page_files, parse_space_folder_from_parent


# 默认输入目录（hybrid 输出）
DEFAULT_INPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"
# 默认输出目录（enrichment 输出）
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid_enriched"
# 默认鉴权文件
DEFAULT_AUTH_STATE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "folder_patents_auth.json"
# 默认 Cookie 文件
DEFAULT_COOKIE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
# 默认浏览器可执行路径
DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# 默认用户目录
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
# 默认是否无头
DEFAULT_HEADLESS = False
# 默认请求超时
DEFAULT_TIMEOUT_SECONDS = 30.0
# 默认重试次数
DEFAULT_RETRY_COUNT = 3
# 默认重试回退基数
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 1.0
# 默认请求间隔
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.2
# 默认请求抖动
DEFAULT_REQUEST_JITTER_SECONDS = 0.4
# 默认请求并发
DEFAULT_REQUEST_CONCURRENCY = 5
# 默认最大鉴权刷新次数
DEFAULT_MAX_AUTH_REFRESHES = 5
# 默认代理
DEFAULT_PROXY: str | None = None
# 默认 resume
DEFAULT_RESUME = True
# 默认鉴权截获超时（毫秒）
DEFAULT_CAPTURE_TIMEOUT_MS = 45000

# 站点初始化参数
DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
DEFAULT_GOTO_TIMEOUT_MS = 30000
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0

# 默认请求头参数
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)
DEFAULT_X_API_VERSION = "2.0"
DEFAULT_X_SITE_LANG = "CN"
DEFAULT_ANALYTICS_ORIGIN = "https://analytics.zhihuiya.com"
DEFAULT_ANALYTICS_REFERER = "https://analytics.zhihuiya.com/"
DEFAULT_ANALYTICS_X_PATSNAP_FROM = "w-analytics-patent-view"

# 默认摘要请求配置
DEFAULT_ABSTRACT_REQUEST_URL = "https://search-service.zhihuiya.com/core-search-api/search/translate/patent"
DEFAULT_ABSTRACT_REQUEST_TEMPLATE = {
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

# 默认 basic 请求体模板
DEFAULT_BASIC_REQUEST_BODY_TEMPLATE = {
    "lang": "CN",
    "original": False,
    "product": "Analytics",
    "view_type": "workspace",
    "source_type": "workspace",
    "_type": "workspace",
    "workspace_id": "ccb6031b05034c7ab2c4b120c2dc3155",
    "highlight": True,
    "shareFrom": "VIEW",
    "date": "20260410T034642Z",
    "expire": "94608000",
    "shareId": "FGBB71D62FEF8EF82F7238F08BF528EC",
    "version": "1.0",
}

# 是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run folder patents enrichment task.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--auth-state-file", type=Path, default=DEFAULT_AUTH_STATE_FILE)
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_FILE)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retry-count", type=int, default=DEFAULT_RETRY_COUNT)
    parser.add_argument("--retry-backoff-base-seconds", type=float, default=DEFAULT_RETRY_BACKOFF_BASE_SECONDS)
    parser.add_argument("--min-request-interval-seconds", type=float, default=DEFAULT_MIN_REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--request-jitter-seconds", type=float, default=DEFAULT_REQUEST_JITTER_SECONDS)
    parser.add_argument("--request-concurrency", type=int, default=DEFAULT_REQUEST_CONCURRENCY)
    parser.add_argument("--max-auth-refreshes", type=int, default=DEFAULT_MAX_AUTH_REFRESHES)
    parser.add_argument("--proxy", default=DEFAULT_PROXY)
    parser.add_argument("--resume", action="store_true", default=DEFAULT_RESUME)
    parser.add_argument("--capture-timeout-ms", type=int, default=DEFAULT_CAPTURE_TIMEOUT_MS)
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    if args.use_defaults == 0:
        return args
    args.input_root = DEFAULT_INPUT_ROOT
    args.output_root = DEFAULT_OUTPUT_ROOT
    args.auth_state_file = DEFAULT_AUTH_STATE_FILE
    args.cookie_file = DEFAULT_COOKIE_FILE
    args.browser_executable_path = DEFAULT_BROWSER_EXECUTABLE_PATH
    args.user_data_dir = DEFAULT_USER_DATA_DIR
    args.headless = DEFAULT_HEADLESS
    args.timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    args.retry_count = DEFAULT_RETRY_COUNT
    args.retry_backoff_base_seconds = DEFAULT_RETRY_BACKOFF_BASE_SECONDS
    args.min_request_interval_seconds = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS
    args.request_jitter_seconds = DEFAULT_REQUEST_JITTER_SECONDS
    args.request_concurrency = DEFAULT_REQUEST_CONCURRENCY
    args.max_auth_refreshes = DEFAULT_MAX_AUTH_REFRESHES
    args.proxy = DEFAULT_PROXY
    args.resume = DEFAULT_RESUME
    args.capture_timeout_ms = DEFAULT_CAPTURE_TIMEOUT_MS
    return args


def build_auth_refresh_config(config: ExistingOutputEnrichmentConfig) -> HybridTaskConfig:
    return HybridTaskConfig(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
        cookie_file=config.cookie_file,
        auth_state_file=config.auth_state_file,
        output_root=str(config.output_root),
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
    if auth_state is not None:
        return auth_state
    if not page_files:
        raise ValueError("no page files found under input root")

    space_id, folder_id = parse_space_folder_from_parent(page_files[0].parent)
    if not space_id or not folder_id:
        raise ValueError(f"unable to parse space_id/folder_id from {page_files[0].parent}")

    logger.info(
        "[folder_patents_enrichment_task] auth cache missing, capture from browser context: space_id={} folder_id={}",
        space_id,
        folder_id,
    )
    return await refresh_auth_state(managed, build_auth_refresh_config(config), space_id, folder_id)


def build_request_headers(config: ExistingOutputEnrichmentConfig, auth_state: FolderAuthState) -> tuple[dict[str, str], dict[str, str]]:
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


def build_config(args: argparse.Namespace) -> ExistingOutputEnrichmentConfig:
    return ExistingOutputEnrichmentConfig(
        input_root=args.input_root,
        output_root=args.output_root,
        auth_state_file=args.auth_state_file,
        cookie_file=args.cookie_file,
        browser_executable_path=args.browser_executable_path,
        user_data_dir=args.user_data_dir,
        target_home_url=DEFAULT_TARGET_HOME_URL,
        success_url=DEFAULT_SUCCESS_URL,
        success_header_selector=DEFAULT_SUCCESS_HEADER_SELECTOR,
        success_logged_in_selector=DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
        success_content_selector=DEFAULT_SUCCESS_CONTENT_SELECTOR,
        loading_overlay_selector=DEFAULT_LOADING_OVERLAY_SELECTOR,
        goto_timeout_ms=DEFAULT_GOTO_TIMEOUT_MS,
        login_timeout_seconds=DEFAULT_LOGIN_TIMEOUT_SECONDS,
        login_poll_interval_seconds=DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
        capture_timeout_ms=args.capture_timeout_ms,
        max_auth_refreshes=args.max_auth_refreshes,
        headless=args.headless,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
        retry_backoff_base_seconds=args.retry_backoff_base_seconds,
        min_request_interval_seconds=args.min_request_interval_seconds,
        request_jitter_seconds=args.request_jitter_seconds,
        resume=args.resume,
        proxy=args.proxy,
        user_agent=DEFAULT_USER_AGENT,
        x_api_version=DEFAULT_X_API_VERSION,
        x_site_lang=DEFAULT_X_SITE_LANG,
        analytics_origin=DEFAULT_ANALYTICS_ORIGIN,
        analytics_referer=DEFAULT_ANALYTICS_REFERER,
        analytics_x_patsnap_from=DEFAULT_ANALYTICS_X_PATSNAP_FROM,
        abstract_request_url=DEFAULT_ABSTRACT_REQUEST_URL,
        abstract_request_template=DEFAULT_ABSTRACT_REQUEST_TEMPLATE,
        basic_request_body_template=DEFAULT_BASIC_REQUEST_BODY_TEMPLATE,
        request_concurrency=args.request_concurrency,
    )


async def run_existing_output_enrichment(config: ExistingOutputEnrichmentConfig) -> Path:
    from playwright.async_api import async_playwright

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
                output_path = build_enrichment_page_path(config.output_root, config.input_root, page_file)
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
                            "failure_count": len(supplement_payload.get("failures", [])),
                        }
                    )
                except Exception as exc:
                    logger.exception("[folder_patents_enrichment_task] page failed: {}", page_file)
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


async def run_task(args: argparse.Namespace) -> Path:
    config = build_config(args)
    step = await run_step_async(
        run_existing_output_enrichment,
        config,
        step_name="执行专利补充信息抓取",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    summary_path = step.value
    if summary_path is None:
        raise RuntimeError("folder patents enrichment task did not return summary path")
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    summary_path = asyncio.run(run_task(args))
    logger.info("[folder_patents_enrichment_task] done: summary={}", summary_path)


if __name__ == "__main__":
    main()

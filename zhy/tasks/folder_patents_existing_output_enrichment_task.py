import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.common.run_step import run_step_async
from zhy.modules.folder_patents_enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.folder_patents_enrichment.workflow import run_existing_output_enrichment


DEFAULT_OUTPUT_DATE_LAYER = date.today().strftime("%Y-%m")
# 默认输入目录，来自已抓取的 folder_patents_hybrid 输出。
DEFAULT_INPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / DEFAULT_OUTPUT_DATE_LAYER / "folder_patents_hybrid"
# 默认输出目录，镜像保存仅含 ABST/ISD 的补充结果。
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / DEFAULT_OUTPUT_DATE_LAYER / "folder_patents_hybrid_enriched"
# 默认鉴权与 cookie 缓存文件，若不存在会由浏览器上下文自动生成。
DEFAULT_AUTH_STATE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "folder_patents_auth.json"
DEFAULT_COOKIE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"

# 默认浏览器上下文参数，沿用 hybrid task 的管理方式。
DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
DEFAULT_GOTO_TIMEOUT_MS = 30000
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0
DEFAULT_CAPTURE_TIMEOUT_MS = 45000
DEFAULT_MAX_AUTH_REFRESHES = 5
DEFAULT_HEADLESS = False

# 默认 analytics 场景请求头。
DEFAULT_ANALYTICS_ORIGIN = "https://analytics.zhihuiya.com"
DEFAULT_ANALYTICS_REFERER = "https://analytics.zhihuiya.com/"
DEFAULT_ANALYTICS_X_PATSNAP_FROM = "w-analytics-patent-view"
DEFAULT_X_API_VERSION = "2.0"
DEFAULT_X_SITE_LANG = "CN"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)

# 默认摘要请求配置。
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
    "date": "20260410T034642Z",
    "expire": "94608000",
    "shareId": "FGBB71D62FEF8EF82F7238F08BF528EC",
    "version": "1.0",
}

# 默认 basic 请求体模板，先按 analytics 页面同类上下文复用。
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

# 默认请求控制参数。
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 1.0
DEFAULT_REQUEST_CONCURRENCY = 5
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.2
DEFAULT_REQUEST_JITTER_SECONDS = 0.4
DEFAULT_RESUME = True
DEFAULT_PROXY = None

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan existing hybrid output and write mirrored supplement pages containing ABST and ISD."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--auth-state-file", type=Path, default=DEFAULT_AUTH_STATE_FILE)
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_FILE)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retry-count", type=int, default=DEFAULT_RETRY_COUNT)
    parser.add_argument("--retry-backoff-base-seconds", type=float, default=DEFAULT_RETRY_BACKOFF_BASE_SECONDS)
    parser.add_argument("--request-concurrency", type=int, default=DEFAULT_REQUEST_CONCURRENCY)
    parser.add_argument("--min-request-interval-seconds", type=float, default=DEFAULT_MIN_REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--request-jitter-seconds", type=float, default=DEFAULT_REQUEST_JITTER_SECONDS)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=DEFAULT_RESUME)
    parser.add_argument("--proxy", default=DEFAULT_PROXY)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    return parser


def build_config(args: argparse.Namespace) -> ExistingOutputEnrichmentConfig:
    """把命令行参数转换为模块运行配置对象。"""

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
        capture_timeout_ms=DEFAULT_CAPTURE_TIMEOUT_MS,
        max_auth_refreshes=DEFAULT_MAX_AUTH_REFRESHES,
        headless=args.headless,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
        retry_backoff_base_seconds=args.retry_backoff_base_seconds,
        request_concurrency=args.request_concurrency,
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
    )


async def run_task(args: argparse.Namespace) -> Path:
    # 以模块为单位执行补充流程，失败则中止。
    workflow_step = await run_step_async(
        run_existing_output_enrichment,
        build_config(args),
        step_name="扫描现有输出并补充ABST与ISD",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )

    summary_path = workflow_step.value
    if summary_path is None:
        raise RuntimeError("existing output enrichment did not return a summary path")
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    summary_path = asyncio.run(run_task(args))
    logger.info("[folder_patents_existing_output_enrichment_task] done: summary={}", summary_path)


if __name__ == "__main__":
    main()

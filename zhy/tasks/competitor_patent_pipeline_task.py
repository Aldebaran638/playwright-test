import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.common.run_step import run_step_async
from zhy.modules.competitor_patent_pipeline.models import CompetitorPatentPipelineConfig
from zhy.modules.competitor_patent_pipeline.workflow import run_competitor_patent_pipeline


# 默认月份，后续按公开/公告日期 PBD 的 YYYY-MM 使用。
DEFAULT_MONTH = "2026-02"
DEFAULT_OUTPUT_DATE_LAYER = DEFAULT_MONTH
# 默认浏览器可执行文件路径，便于本地直接复用已安装浏览器。
DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# 默认用户数据目录，便于复用已有登录态。
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
# 默认 Cookie 文件路径。
DEFAULT_COOKIE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
# 默认鉴权缓存文件路径，供后续步骤复用。
DEFAULT_AUTH_STATE_FILE = PROJECT_ROOT / "zhy" / "data" / "other" / "folder_patents_auth.json"
# 默认法律状态映射文件。
DEFAULT_LEGAL_STATUS_MAPPING_FILE = PROJECT_ROOT / "zhy" / "data" / "tmp" / "mid1.json"


def build_output_paths(date_layer: str) -> tuple[Path, Path, Path, Path, Path, Path]:
    base_output = PROJECT_ROOT / "zhy" / "data" / "output" / date_layer
    return (
        base_output / "folder_patents_hybrid",
        base_output / "folder_patents_hybrid_enriched",
        base_output / "competitor_patent_pipeline" / "competitor_folder_mapping.json",
        base_output / "competitor_patent_pipeline" / "competitor_folder_mapping_raw.json",
        base_output / "excel_reports",
        base_output / "competitor_patent_pipeline",
    )


(
    DEFAULT_ORIGINAL_OUTPUT_ROOT,
    DEFAULT_ENRICHED_OUTPUT_ROOT,
    DEFAULT_FOLDER_MAPPING_FILE,
    DEFAULT_FOLDER_MAPPING_RAW_FILE,
    DEFAULT_REPORT_OUTPUT_DIR,
    DEFAULT_PIPELINE_OUTPUT_DIR,
) = build_output_paths(DEFAULT_OUTPUT_DATE_LAYER)

# 默认 workspace 空间 id。
DEFAULT_WORKSPACE_SPACE_ID = "ccb6031b05034c7ab2c4b120c2dc3155"
# 默认竞争对手父文件夹 id，只保留其直接子文件夹作为有效竞争对手。
DEFAULT_COMPETITOR_PARENT_FOLDER_ID = "8614f137547f4e46b8557ae8d3b1e1f5"
# 默认竞争对手列表页面 URL。
DEFAULT_COMPETITOR_LIST_PAGE_URL = (
    "https://workspace.zhihuiya.com/detail/patent/default"
    f"?spaceId={DEFAULT_WORKSPACE_SPACE_ID}"
)
# 默认竞争对手列表请求 URL。
DEFAULT_COMPETITOR_LIST_REQUEST_URL = (
    "https://workspace-service.zhihuiya.com/workspace/web/space/"
    f"{DEFAULT_WORKSPACE_SPACE_ID}/folder-list"
)
# 默认 workspace 请求 Origin。
DEFAULT_WORKSPACE_ORIGIN = "https://workspace.zhihuiya.com"
# 默认 workspace 请求 Referer。
DEFAULT_WORKSPACE_REFERER = "https://workspace.zhihuiya.com/"
# 默认 workspace 站点语言。
DEFAULT_WORKSPACE_X_SITE_LANG = "CN"
# 默认 workspace API 版本头。
DEFAULT_WORKSPACE_X_API_VERSION = "2.0"
# 默认 workspace 来源标识头。
DEFAULT_WORKSPACE_X_PATSNAP_FROM = "w-analytics-workspace"
# 默认 workspace User-Agent。
DEFAULT_WORKSPACE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)

# analytics 补充信息请求默认头。
DEFAULT_ANALYTICS_ORIGIN = "https://analytics.zhihuiya.com"
DEFAULT_ANALYTICS_REFERER = "https://analytics.zhihuiya.com/"
DEFAULT_ANALYTICS_X_PATSNAP_FROM = "w-analytics-patent-view"

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
    "date": "20260310T034642Z",
    "expire": "94608000",
    "shareId": "FGBB71D62FEF8EF82F7238F08BF528EC",
    "version": "1.0",
}

# 默认 basic 请求体模板。
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

# 站点初始化目标 URL。
DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
# 登录成功后应到达的 URL。
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
# 登录成功头部元素选择器。
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
# 登录成功头像元素选择器。
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
# 登录成功主内容元素选择器。
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
# 登录过程中的遮罩元素选择器。
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
# 首次打开页面超时时间（毫秒）。
DEFAULT_GOTO_TIMEOUT_MS = 30000
# 登录等待总超时（秒）。
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
# 登录轮询间隔（秒）。
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0
# 竞争对手列表请求截获超时（毫秒）。
DEFAULT_COMPETITOR_LIST_CAPTURE_TIMEOUT_MS = 45000

# 按月专利抓取默认起始页。
DEFAULT_PATENTS_START_PAGE = 1
# 按月专利抓取默认每页条数。
DEFAULT_PATENTS_PAGE_SIZE = 100
# 按月专利抓取默认排序：按公开日期倒序。
DEFAULT_PATENTS_SORT = "pdesc"
# 按月专利抓取默认视图类型。
DEFAULT_PATENTS_VIEW_TYPE = "tablelist"
# 按月专利抓取默认 is_init。
DEFAULT_PATENTS_IS_INIT = True
# 按月专利抓取默认 standard_only。
DEFAULT_PATENTS_STANDARD_ONLY = False
# 按月专利抓取默认请求超时（秒）。
DEFAULT_PATENTS_TIMEOUT_SECONDS = 30.0
# 按月专利抓取默认鉴权截获超时（毫秒）。
DEFAULT_PATENTS_CAPTURE_TIMEOUT_MS = 45000
# 按月专利抓取默认最大鉴权刷新次数。
DEFAULT_PATENTS_MAX_AUTH_REFRESHES = 5
# 按月专利抓取默认请求重试次数。
DEFAULT_PATENTS_RETRY_COUNT = 3
# 按月专利抓取默认重试回退基数（秒）。
DEFAULT_PATENTS_RETRY_BACKOFF_BASE_SECONDS = 1.0
# 按月专利抓取默认最小请求间隔（秒）。
DEFAULT_PATENTS_MIN_REQUEST_INTERVAL_SECONDS = 1.2
# 按月专利抓取默认请求抖动上限（秒）。
DEFAULT_PATENTS_REQUEST_JITTER_SECONDS = 0.4
# 按月专利抓取默认代理。
DEFAULT_PATENTS_PROXY = None
# 按月专利抓取默认公司级并发数。
DEFAULT_PATENTS_COMPANY_CONCURRENCY = 5
# 按月专利抓取默认测试公司 folder_id 列表；为空表示跑全部公司。
DEFAULT_PATENTS_TEST_FOLDER_IDS: list[str] = [ ]

# 默认是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1
# 默认是否无头运行浏览器。
DEFAULT_HEADLESS = False
# 默认补充信息阶段是否跳过已生成结果。
DEFAULT_ENRICHMENT_RESUME = True
# 默认补充信息阶段并发数。
DEFAULT_ENRICHMENT_REQUEST_CONCURRENCY = 5

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the competitor patent monthly pipeline. Current stage executes login first.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--month", default=DEFAULT_MONTH)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_FILE)
    parser.add_argument("--auth-state-file", type=Path, default=DEFAULT_AUTH_STATE_FILE)
    parser.add_argument("--original-output-root", type=Path, default=DEFAULT_ORIGINAL_OUTPUT_ROOT)
    parser.add_argument("--enriched-output-root", type=Path, default=DEFAULT_ENRICHED_OUTPUT_ROOT)
    parser.add_argument("--folder-mapping-file", type=Path, default=DEFAULT_FOLDER_MAPPING_FILE)
    parser.add_argument("--folder-mapping-raw-file", type=Path, default=DEFAULT_FOLDER_MAPPING_RAW_FILE)
    parser.add_argument("--legal-status-mapping-file", type=Path, default=DEFAULT_LEGAL_STATUS_MAPPING_FILE)
    parser.add_argument("--report-output-dir", type=Path, default=DEFAULT_REPORT_OUTPUT_DIR)
    parser.add_argument("--pipeline-output-dir", type=Path, default=DEFAULT_PIPELINE_OUTPUT_DIR)
    parser.add_argument("--workspace-space-id", default=DEFAULT_WORKSPACE_SPACE_ID)
    parser.add_argument("--competitor-parent-folder-id", default=DEFAULT_COMPETITOR_PARENT_FOLDER_ID)
    parser.add_argument("--competitor-list-page-url", default=DEFAULT_COMPETITOR_LIST_PAGE_URL)
    parser.add_argument("--competitor-list-request-url", default=DEFAULT_COMPETITOR_LIST_REQUEST_URL)
    parser.add_argument("--workspace-origin", default=DEFAULT_WORKSPACE_ORIGIN)
    parser.add_argument("--workspace-referer", default=DEFAULT_WORKSPACE_REFERER)
    parser.add_argument("--workspace-x-site-lang", default=DEFAULT_WORKSPACE_X_SITE_LANG)
    parser.add_argument("--workspace-x-api-version", default=DEFAULT_WORKSPACE_X_API_VERSION)
    parser.add_argument("--workspace-x-patsnap-from", default=DEFAULT_WORKSPACE_X_PATSNAP_FROM)
    parser.add_argument("--workspace-user-agent", default=DEFAULT_WORKSPACE_USER_AGENT)
    parser.add_argument("--patents-start-page", type=int, default=DEFAULT_PATENTS_START_PAGE)
    parser.add_argument("--patents-page-size", type=int, default=DEFAULT_PATENTS_PAGE_SIZE)
    parser.add_argument("--patents-sort", default=DEFAULT_PATENTS_SORT)
    parser.add_argument("--patents-view-type", default=DEFAULT_PATENTS_VIEW_TYPE)
    parser.add_argument("--patents-is-init", type=int, choices=[0, 1], default=1 if DEFAULT_PATENTS_IS_INIT else 0)
    parser.add_argument("--patents-standard-only", type=int, choices=[0, 1], default=1 if DEFAULT_PATENTS_STANDARD_ONLY else 0)
    parser.add_argument("--patents-timeout-seconds", type=float, default=DEFAULT_PATENTS_TIMEOUT_SECONDS)
    parser.add_argument("--patents-capture-timeout-ms", type=int, default=DEFAULT_PATENTS_CAPTURE_TIMEOUT_MS)
    parser.add_argument("--patents-max-auth-refreshes", type=int, default=DEFAULT_PATENTS_MAX_AUTH_REFRESHES)
    parser.add_argument("--patents-retry-count", type=int, default=DEFAULT_PATENTS_RETRY_COUNT)
    parser.add_argument("--patents-retry-backoff-base-seconds", type=float, default=DEFAULT_PATENTS_RETRY_BACKOFF_BASE_SECONDS)
    parser.add_argument("--patents-min-request-interval-seconds", type=float, default=DEFAULT_PATENTS_MIN_REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--patents-request-jitter-seconds", type=float, default=DEFAULT_PATENTS_REQUEST_JITTER_SECONDS)
    parser.add_argument("--patents-proxy", default=DEFAULT_PATENTS_PROXY)
    parser.add_argument("--patents-company-concurrency", type=int, default=DEFAULT_PATENTS_COMPANY_CONCURRENCY)
    parser.add_argument("--patents-test-folder-id", action="append", dest="patents_test_folder_ids", default=[])
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    """简介：按 use-defaults 开关决定是否强制回落到流程文件默认参数。
    参数：args 为命令行参数对象。
    返回值：处理后的参数对象。
    逻辑：当 use-defaults=1 时，统一覆盖为流程文件硬编码默认值，便于直接跑总流程。
    """

    # 显式关闭默认模式时，保留外部传入的命令行参数。
    if args.use_defaults == 0:
        return args

    # 打开默认模式时，统一回落到流程文件里硬编码的参数。
    args.month = DEFAULT_MONTH
    args.browser_executable_path = DEFAULT_BROWSER_EXECUTABLE_PATH
    args.user_data_dir = DEFAULT_USER_DATA_DIR
    args.cookie_file = DEFAULT_COOKIE_FILE
    args.auth_state_file = DEFAULT_AUTH_STATE_FILE
    args.original_output_root = DEFAULT_ORIGINAL_OUTPUT_ROOT
    args.enriched_output_root = DEFAULT_ENRICHED_OUTPUT_ROOT
    args.folder_mapping_file = DEFAULT_FOLDER_MAPPING_FILE
    args.folder_mapping_raw_file = DEFAULT_FOLDER_MAPPING_RAW_FILE
    args.legal_status_mapping_file = DEFAULT_LEGAL_STATUS_MAPPING_FILE
    args.report_output_dir = DEFAULT_REPORT_OUTPUT_DIR
    args.pipeline_output_dir = DEFAULT_PIPELINE_OUTPUT_DIR
    args.workspace_space_id = DEFAULT_WORKSPACE_SPACE_ID
    args.competitor_parent_folder_id = DEFAULT_COMPETITOR_PARENT_FOLDER_ID
    args.competitor_list_page_url = DEFAULT_COMPETITOR_LIST_PAGE_URL
    args.competitor_list_request_url = DEFAULT_COMPETITOR_LIST_REQUEST_URL
    args.workspace_origin = DEFAULT_WORKSPACE_ORIGIN
    args.workspace_referer = DEFAULT_WORKSPACE_REFERER
    args.workspace_x_site_lang = DEFAULT_WORKSPACE_X_SITE_LANG
    args.workspace_x_api_version = DEFAULT_WORKSPACE_X_API_VERSION
    args.workspace_x_patsnap_from = DEFAULT_WORKSPACE_X_PATSNAP_FROM
    args.workspace_user_agent = DEFAULT_WORKSPACE_USER_AGENT
    args.patents_start_page = DEFAULT_PATENTS_START_PAGE
    args.patents_page_size = DEFAULT_PATENTS_PAGE_SIZE
    args.patents_sort = DEFAULT_PATENTS_SORT
    args.patents_view_type = DEFAULT_PATENTS_VIEW_TYPE
    args.patents_is_init = 1 if DEFAULT_PATENTS_IS_INIT else 0
    args.patents_standard_only = 1 if DEFAULT_PATENTS_STANDARD_ONLY else 0
    args.patents_timeout_seconds = DEFAULT_PATENTS_TIMEOUT_SECONDS
    args.patents_capture_timeout_ms = DEFAULT_PATENTS_CAPTURE_TIMEOUT_MS
    args.patents_max_auth_refreshes = DEFAULT_PATENTS_MAX_AUTH_REFRESHES
    args.patents_retry_count = DEFAULT_PATENTS_RETRY_COUNT
    args.patents_retry_backoff_base_seconds = DEFAULT_PATENTS_RETRY_BACKOFF_BASE_SECONDS
    args.patents_min_request_interval_seconds = DEFAULT_PATENTS_MIN_REQUEST_INTERVAL_SECONDS
    args.patents_request_jitter_seconds = DEFAULT_PATENTS_REQUEST_JITTER_SECONDS
    args.patents_proxy = DEFAULT_PATENTS_PROXY
    args.patents_company_concurrency = DEFAULT_PATENTS_COMPANY_CONCURRENCY
    args.patents_test_folder_ids = list(DEFAULT_PATENTS_TEST_FOLDER_IDS)
    args.headless = DEFAULT_HEADLESS
    return args


def build_config(args: argparse.Namespace) -> CompetitorPatentPipelineConfig:
    """简介：把命令行参数转换为总流程模块配置对象。
    参数：args 为命令行参数对象。
    返回值：CompetitorPatentPipelineConfig。
    逻辑：当前总流程只执行登录步骤，但先把后续步骤要用的参数也统一收口到配置里。
    """

    return CompetitorPatentPipelineConfig(
        month=args.month,
        browser_executable_path=args.browser_executable_path,
        user_data_dir=args.user_data_dir,
        cookie_file=args.cookie_file,
        auth_state_file=args.auth_state_file,
        original_output_root=args.original_output_root,
        enriched_output_root=args.enriched_output_root,
        folder_mapping_file=args.folder_mapping_file,
        folder_mapping_raw_file=args.folder_mapping_raw_file,
        legal_status_mapping_file=args.legal_status_mapping_file,
        report_output_dir=args.report_output_dir,
        pipeline_output_dir=args.pipeline_output_dir,
        workspace_space_id=args.workspace_space_id,
        competitor_parent_folder_id=args.competitor_parent_folder_id,
        competitor_list_page_url=args.competitor_list_page_url,
        competitor_list_request_url=args.competitor_list_request_url,
        workspace_origin=args.workspace_origin,
        workspace_referer=args.workspace_referer,
        workspace_x_site_lang=args.workspace_x_site_lang,
        workspace_x_api_version=args.workspace_x_api_version,
        workspace_x_patsnap_from=args.workspace_x_patsnap_from,
        workspace_user_agent=args.workspace_user_agent,
        analytics_origin=DEFAULT_ANALYTICS_ORIGIN,
        analytics_referer=DEFAULT_ANALYTICS_REFERER,
        analytics_x_patsnap_from=DEFAULT_ANALYTICS_X_PATSNAP_FROM,
        abstract_request_url=DEFAULT_ABSTRACT_REQUEST_URL,
        abstract_request_template=DEFAULT_ABSTRACT_REQUEST_TEMPLATE,
        basic_request_body_template=DEFAULT_BASIC_REQUEST_BODY_TEMPLATE,
        enrichment_resume=DEFAULT_ENRICHMENT_RESUME,
        enrichment_request_concurrency=DEFAULT_ENRICHMENT_REQUEST_CONCURRENCY,
        target_home_url=DEFAULT_TARGET_HOME_URL,
        success_url=DEFAULT_SUCCESS_URL,
        success_header_selector=DEFAULT_SUCCESS_HEADER_SELECTOR,
        success_logged_in_selector=DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
        success_content_selector=DEFAULT_SUCCESS_CONTENT_SELECTOR,
        loading_overlay_selector=DEFAULT_LOADING_OVERLAY_SELECTOR,
        goto_timeout_ms=DEFAULT_GOTO_TIMEOUT_MS,
        login_timeout_seconds=DEFAULT_LOGIN_TIMEOUT_SECONDS,
        login_poll_interval_seconds=DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
        competitor_list_capture_timeout_ms=DEFAULT_COMPETITOR_LIST_CAPTURE_TIMEOUT_MS,
        patents_start_page=args.patents_start_page,
        patents_page_size=args.patents_page_size,
        patents_sort=args.patents_sort,
        patents_view_type=args.patents_view_type,
        patents_is_init=bool(args.patents_is_init),
        patents_standard_only=bool(args.patents_standard_only),
        patents_timeout_seconds=args.patents_timeout_seconds,
        patents_capture_timeout_ms=args.patents_capture_timeout_ms,
        patents_max_auth_refreshes=args.patents_max_auth_refreshes,
        patents_retry_count=args.patents_retry_count,
        patents_retry_backoff_base_seconds=args.patents_retry_backoff_base_seconds,
        patents_min_request_interval_seconds=args.patents_min_request_interval_seconds,
        patents_request_jitter_seconds=args.patents_request_jitter_seconds,
        patents_proxy=args.patents_proxy,
        patents_company_concurrency=args.patents_company_concurrency,
        patents_test_folder_ids=list(args.patents_test_folder_ids),
        headless=args.headless,
    )


async def run_task(args: argparse.Namespace) -> Path:
    """简介：执行竞争对手专利总流程 task。
    参数：args 为已解析的流程参数。
    返回值：本次运行 summary 文件路径。
    逻辑：当前先完成登录，再抓取竞争对手列表，并输出阶段性 summary。
    """

    workflow_step = await run_step_async(
        run_competitor_patent_pipeline,
        build_config(args),
        step_name="执行竞争对手专利总流程-登录初始化",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    summary_path = workflow_step.value
    if summary_path is None:
        raise RuntimeError("competitor patent pipeline task did not return a summary path")
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    summary_path = asyncio.run(run_task(args))
    logger.info("[competitor_patent_pipeline_task] done: summary={}", summary_path)


if __name__ == "__main__":
    # 直接执行任务文件时，从这里进入总流程。
    main()

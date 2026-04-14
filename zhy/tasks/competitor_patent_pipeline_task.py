import argparse
import asyncio
import os
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
from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError
from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig
from zhy.modules.common.types.translation import OpenAICompatibleClientConfig
from zhy.modules.fetch.competitor_folder_mapping import fetch_competitor_folder_mapping
from zhy.modules.fetch.folder_patents_api import RequestScheduler
from zhy.modules.fetch.folder_patents_auth import refresh_auth_state
from zhy.modules.fetch.monthly_patents import run_monthly_patent_fetch
from zhy.modules.fetch.patent_basic import build_page_supplement_payload
from zhy.modules.fetch.legal_status_mapping import refresh_legal_status_mapping_file
from zhy.modules.init.enrichment_auth import ensure_enrichment_auth_state
from zhy.modules.init.pipeline_login import ensure_pipeline_logged_in
from zhy.modules.persist.auth_state_io import load_auth_state_from_file
from zhy.modules.persist.json_io import load_json_file_any_utf, save_json
from zhy.modules.persist.page_path import (
    build_enrichment_page_path,
    has_existing_page_files,
    iter_input_page_files,
    parse_space_folder_from_parent,
)
from zhy.modules.report.competitor_patent_report import run_competitor_patent_report
from zhy.modules.transform.competitor_patent_pipeline import (
    build_patent_abstract_translation_config,
    build_competitor_patent_report_config,
    build_existing_output_enrichment_config,
    build_monthly_auth_config,
    load_pages_written,
)
from zhy.modules.transform.enrichment import (
    build_enrichment_auth_refresh_config,
    build_enrichment_request_headers,
)
from zhy.modules.transform.translate_patent_abstracts import run_translate_patent_abstracts


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
def build_output_paths(date_layer: str) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
    """简介：按日期层构建月度流程的 6 个标准输出目录。
    参数：date_layer 为 YYYY-MM 格式的日期字符串。
    返回值：7 元组 (原始输出根、补充信息输出根、翻译输出根、文件夹映射、原始映射、报告输出、流程输出)。
    逻辑：所有目录均按日期分层，便于多月份运行时自动隔离结果。
    """
    base_output = PROJECT_ROOT / "zhy" / "data" / "output" / date_layer
    return (
        base_output / "folder_patents_hybrid",
        base_output / "folder_patents_hybrid_enriched",
        base_output / "folder_patents_hybrid_translated",
        base_output / "competitor_patent_pipeline" / "competitor_folder_mapping.json",
        base_output / "competitor_patent_pipeline" / "competitor_folder_mapping_raw.json",
        base_output / "competitor_patent_pipeline" / "legal_status_mapping.json",
        base_output / "excel_reports",
        base_output / "competitor_patent_pipeline",
    )


(
    DEFAULT_ORIGINAL_OUTPUT_ROOT,
    DEFAULT_ENRICHED_OUTPUT_ROOT,
    DEFAULT_TRANSLATED_OUTPUT_ROOT,
    DEFAULT_FOLDER_MAPPING_FILE,
    DEFAULT_FOLDER_MAPPING_RAW_FILE,
    DEFAULT_LEGAL_STATUS_MAPPING_FILE,
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
DEFAULT_PATENTS_TEST_FOLDER_IDS: list[str] = [
    "f3abc32038024c398b27fbc853ddb205",
    "01d62c65b6004f12b53dc784a8c7c3db",
    "5b8f65fdf98f485b9be7fae53b5f6ed6",
    "dc7b61795b0e47be8962d13b799a21c7",
    "f2dc68c92d574b1f848f2266033b014a",
    "b331ddec5e6c49e59164bfe4fa132427",
    "1144dcc625ed489ebe790ba2e254f93d",
    "e63beb68be7f462cac8af8fe51a8df2b",
    "5d4c2efe21fa4d2aa373c45baa5d61d8",
    "4b40c13a4e3540f2a728c86d2bfbb2a0",
    "5ec96a5a1736450b8b0c2342e251e102",
    "3e2addf18de94f06a56580f3b130fba5",
    "ee6b594b828140f3a68f2cc0f72d361d",
    "336870f58f784cf4b4c549ce0f89316a",
    "009169ef5aee4a43bec38f62cc14f4db",
    "cb0c191101a2433bb624a75f267d42b6",
    "65f1ca9627d440d7926106e39bb2c594",
    "9bb085bc5e80483aa74a27f51c913669",
    "d187d0a086cd4a92a109f80500226124",
    "d99392d0fe564269b497d84ed4f31d8e",
    "45cb70936cd24f05bf3f4fb8c3c72966",
    "cf26fac1e28245b8a66b81d7e64a47ac",
    "a249554547b34dc5b4ad82850f544085",
    "1f9454e94df94dd196df0d0988893f7c",
    "1962c8210697401ea9cc4213cec0101d",
    "f34307e6b20c49db8f8927d28485cb67",
    "f784815ff5634edfb8233f09a265ad7a",
    "d7abe8b21119497491117e971748af4e",
    "e5cb6f2045dd4851b748d1e2c4fe7b68",
    "569b56ad2d7d4189a1a6ee5a124b6b04",
    "310b60921f0c4400ab3c878ea664397a",
    "8ae33d07b7d14d0baef1eafe1f0422f6",
    "1044a5104b36448888c1c05a3cda29a9",
    "5c36f7e6fa46431d91b1e34c833cc448",
    "f73f14002fe94bd1a6ab8b0ab427230c",
    "a86a01c2f58d4daa8a0593ae618cab6d",
    "7ccce16780624173ae5a3efc2ef9d647",
    "f5dfc19ec04b47b097ed8beaf6388624",
    "a962bac504ef477396b881710a7eafad",
    "edb9160ef53e49e09cfd34ff73a45589",
    "9cfb7e1877c84906b3379d67b9911065",
    "5c0aefd4596c472e95dc98790174d8b3",
    "787a7346edaa4ffc8fc7ae7a603eb6d6",
    "c45b5a8bd9c9437a8dc6d4c4e9bfa105",
    "750e84c8956f47548185910ef165b8a5",
    "c08a3139e0d248918e5a8b592b81f22b",
    "6d408561684845b8b9fd00b625cf700c",
    "d6f063dcbf0048e1ae71e526e74b3601",
    "5fc0db0d625444f5a83f9231ac6bec6a",
    "2e69f3fc17d7480e8e7134ee7af5467d",
    "718230c735244402baecad348bb0a4bc",
    "01b43cd9dac749e4af81ee6b5d212d76",
    "e95ea4564435411c89ef2d41a52d7ca9",
    "68044c896d0d4ffaaa3ae20a2a675dc8",
    "75b63248203d4295ad71a909fa34cea7",
    "580ad81b850848218970071551fc1a08",
    "33596c1b7b0e445587353da28ac57498",
    "2b21dce05f16400ea7593772148ee06a",
    "4c16bd04d3554bd4ac9d590d885c2237",
    "6caa6b1093fd4615b2606b1203d3baa3",
    "793859e128104b6e974870666a735dae",
    "c2061a741c81430583efefc32e9bfd57",
    "a3acf4cd05484313a17a039be773527b",
    "a2bab93e765e4a20853444797910912a",
    "666aaebea71748509859a860665c38ec",
    "03fbe996aa134fac835bda7b7766c09c",
    "950a15fe004c4fa9a965216acde42676",
    "c88509967b154eaa950b0c96573757e9",
    "5eba3e34aa9b403bbc825a6a72b17fc2",
    "c8ceee9e288740eaaf18988364cd3d56",
    "397bd7fc5aad4e458f6a0452a04bf273",
    "ad4ea54e4f244eee9ac7c0579b18d176",
    "a069713d31694a7ea80771429593290f",
    "30eb6fa113d046c984dfde6c82e905fe",
    "756fc4f5c3344fb5af553d45ff528220",
    "7d6a0bc6b8e940198c66df6fef83842d",
    "57124406db7b4ee3915b1c3113e91dcf",
    "007c18f329fb40d3897d37fa9a82a150",
    "2300624a77364e3abbd0279bd5c72320",
    "71a27f3ef8334824a1ffa55a67e619ab",
    "eb9746f2b28a4832a7711792648bb63b",
    "fd057347bfeb4aacafbcbbb4ffec399a",
    "388b79988a4c4e1b86c48e7fca6a3d49",
    "77d3ebc45ff641769e0ca6867d1c7c98",
    "22db9b3fbb384ac4a1f127b3b7e70f4b",
    "df7bf0881b1544a7a5fb0aa5a92cefee",
    "83004801a39540b9833d5443efbae40d",
    "da49b4d09d784eb7a43790c17611b861",
    "526bb38ad5d34f4b88eb957449c2cc2e",
    "6088f5943a5441b5b48fa96818efc6fe",
    "4fb8c7db6a454ed88c6493cdafac1911",
    "0c30e3cdc9a442368a4fb55a24f2505c",
    "b0b683c182d14e679773e4d1b8ddef8d",
    # "3d980f6f8f224e72a057292f8735c2ee", 欧莱雅
    "ecf86655edc0489592233f22e986088a",
    "0d7b8655db3846b1a21a39dae16f4a59",
    "1486a184ed5f4d3599b251407aaf54a8"
]


# 默认是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1
# 默认是否无头运行浏览器。
DEFAULT_HEADLESS = False
# 默认补充信息阶段是否跳过已生成结果。
DEFAULT_ENRICHMENT_RESUME = True
# 默认补充信息阶段并发数。
DEFAULT_ENRICHMENT_REQUEST_CONCURRENCY = 5
# 默认是否开启摘要翻译步骤。
DEFAULT_ABSTRACT_TRANSLATION_ENABLED = True
# 默认翻译阶段是否跳过已生成结果。
DEFAULT_ABSTRACT_TRANSLATION_RESUME = True
# 默认翻译阶段并发数。
DEFAULT_ABSTRACT_TRANSLATION_REQUEST_CONCURRENCY = 3
# 默认翻译目标语言。
DEFAULT_ABSTRACT_TRANSLATION_TARGET_LANGUAGE = "简体中文"
# 默认 OpenAI 兼容接口配置。
DEFAULT_OPENAI_COMPATIBLE_BASE_URL = "http://192.168.3.242:1995/v1"
DEFAULT_OPENAI_COMPATIBLE_API_KEY = "dummy"
DEFAULT_OPENAI_COMPATIBLE_MODEL = "Qwen3-32B-FP8"
DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS = 60.0
DEFAULT_OPENAI_COMPATIBLE_RETRY_COUNT = 3
DEFAULT_OPENAI_COMPATIBLE_RETRY_BACKOFF_BASE_SECONDS = 2.0

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_argument_parser() -> argparse.ArgumentParser:
    """简介：构建命令行参数解析器。
    参数：无。
    返回值：ArgumentParser 实例。
    逻辑：定义月份、浏览器、路径、请求参数等所有命令行选项。
    """
    parser = argparse.ArgumentParser(description="Run the competitor patent monthly pipeline. Current stage executes login first.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--month", default=DEFAULT_MONTH)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_FILE)
    parser.add_argument("--auth-state-file", type=Path, default=DEFAULT_AUTH_STATE_FILE)
    parser.add_argument("--original-output-root", type=Path, default=DEFAULT_ORIGINAL_OUTPUT_ROOT)
    parser.add_argument("--enriched-output-root", type=Path, default=DEFAULT_ENRICHED_OUTPUT_ROOT)
    parser.add_argument("--translated-output-root", type=Path, default=DEFAULT_TRANSLATED_OUTPUT_ROOT)
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
    parser.add_argument("--enable-abstract-translation", action="store_true", default=DEFAULT_ABSTRACT_TRANSLATION_ENABLED)
    parser.add_argument("--disable-abstract-translation-resume", action="store_true", default=False)
    parser.add_argument("--abstract-translation-request-concurrency", type=int, default=DEFAULT_ABSTRACT_TRANSLATION_REQUEST_CONCURRENCY)
    parser.add_argument("--abstract-translation-target-language", default=DEFAULT_ABSTRACT_TRANSLATION_TARGET_LANGUAGE)
    parser.add_argument("--openai-compatible-base-url", default=DEFAULT_OPENAI_COMPATIBLE_BASE_URL)
    parser.add_argument("--openai-compatible-api-key", default=DEFAULT_OPENAI_COMPATIBLE_API_KEY)
    parser.add_argument("--openai-compatible-model", default=DEFAULT_OPENAI_COMPATIBLE_MODEL)
    parser.add_argument("--openai-compatible-timeout-seconds", type=float, default=DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS)
    parser.add_argument("--openai-compatible-retry-count", type=int, default=DEFAULT_OPENAI_COMPATIBLE_RETRY_COUNT)
    parser.add_argument("--openai-compatible-retry-backoff-base-seconds", type=float, default=DEFAULT_OPENAI_COMPATIBLE_RETRY_BACKOFF_BASE_SECONDS)
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
    args.translated_output_root = DEFAULT_TRANSLATED_OUTPUT_ROOT
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
    args.enable_abstract_translation = DEFAULT_ABSTRACT_TRANSLATION_ENABLED
    args.disable_abstract_translation_resume = not DEFAULT_ABSTRACT_TRANSLATION_RESUME
    args.abstract_translation_request_concurrency = DEFAULT_ABSTRACT_TRANSLATION_REQUEST_CONCURRENCY
    args.abstract_translation_target_language = DEFAULT_ABSTRACT_TRANSLATION_TARGET_LANGUAGE
    args.openai_compatible_base_url = DEFAULT_OPENAI_COMPATIBLE_BASE_URL
    args.openai_compatible_api_key = DEFAULT_OPENAI_COMPATIBLE_API_KEY
    args.openai_compatible_model = DEFAULT_OPENAI_COMPATIBLE_MODEL
    args.openai_compatible_timeout_seconds = DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS
    args.openai_compatible_retry_count = DEFAULT_OPENAI_COMPATIBLE_RETRY_COUNT
    args.openai_compatible_retry_backoff_base_seconds = DEFAULT_OPENAI_COMPATIBLE_RETRY_BACKOFF_BASE_SECONDS
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
        translated_output_root=args.translated_output_root,
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
        abstract_translation_enabled=bool(args.enable_abstract_translation),
        abstract_translation_resume=not bool(args.disable_abstract_translation_resume),
        abstract_translation_request_concurrency=args.abstract_translation_request_concurrency,
        abstract_translation_target_language=args.abstract_translation_target_language,
        abstract_translation_client=(
            None
            if not (
                str(args.openai_compatible_base_url or "").strip()
                and str(args.openai_compatible_api_key or "").strip()
                and str(args.openai_compatible_model or "").strip()
            )
            else OpenAICompatibleClientConfig(
                base_url=str(args.openai_compatible_base_url).strip(),
                api_key=str(args.openai_compatible_api_key).strip(),
                model=str(args.openai_compatible_model).strip(),
                timeout_seconds=args.openai_compatible_timeout_seconds,
                retry_count=args.openai_compatible_retry_count,
                retry_backoff_base_seconds=args.openai_compatible_retry_backoff_base_seconds,
            )
        ),
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


def build_pipeline_summary_payload(
    config: CompetitorPatentPipelineConfig,
    *,
    login_status: str,
    login_final_url: str,
    competitor_list_status: str,
    competitor_list_count: int,
    competitor_list_output: str,
    monthly_patents_status: str,
    monthly_patents_folder_count: int,
    monthly_patents_output: str,
    enrich_patents_status: str,
    enrich_patents_output: str,
    enrich_patents_pages_written: int,
    translate_patents_status: str,
    translate_patents_output: str,
    translate_patents_pages_written: int,
    build_monthly_report_status: str,
    build_monthly_report_output: str,
) -> dict:
    return {
        "month": config.month,
        "paths": {
            "cookie_file": str(config.cookie_file),
            "auth_state_file": str(config.auth_state_file),
            "original_output_root": str(config.original_output_root),
            "enriched_output_root": str(config.enriched_output_root),
            "translated_output_root": str(config.translated_output_root),
            "folder_mapping_file": str(config.folder_mapping_file),
            "folder_mapping_raw_file": str(config.folder_mapping_raw_file),
            "legal_status_mapping_file": str(config.legal_status_mapping_file),
            "report_output_dir": str(config.report_output_dir),
        },
        "steps": [
            {
                "name": "login",
                "status": login_status,
                "final_url": login_final_url,
            },
            {
                "name": "fetch_competitor_list",
                "status": competitor_list_status,
                "count": competitor_list_count,
                "output": competitor_list_output,
            },
            {
                "name": "fetch_monthly_patents",
                "status": monthly_patents_status,
                "folder_count": monthly_patents_folder_count,
                "output": monthly_patents_output,
            },
            {
                "name": "enrich_patents",
                "status": enrich_patents_status,
                "pages_written": enrich_patents_pages_written,
                "output": enrich_patents_output,
            },
            {
                "name": "translate_patent_abstracts",
                "status": translate_patents_status,
                "pages_written": translate_patents_pages_written,
                "output": translate_patents_output,
            },
            {
                "name": "build_monthly_report",
                "status": build_monthly_report_status,
                "output": build_monthly_report_output,
            },
        ],
    }


async def run_existing_output_enrichment(config: ExistingOutputEnrichmentConfig) -> Path:
    """简介：执行现有月度输出的补充信息抓取步骤。
    参数：config 为补充信息阶段配置。
    返回值：补充信息 summary 文件路径。
    逻辑：遍历原始 page 文件，仅补抓 ABST，并把结果镜像写入 enrichment 目录。
    """

    from playwright.async_api import async_playwright

    if not config.input_root.exists():
        raise FileNotFoundError(f"input root not found: {config.input_root}")

    page_files = (
        sorted(config.target_page_files)
        if config.target_page_files is not None
        else iter_input_page_files(config.input_root)
    )

    summary = {
        "input_root": str(config.input_root),
        "output_root": str(config.output_root),
        "auth_state_file": str(config.auth_state_file),
        "total_page_files": len(page_files),
        "pages_written": 0,
        "pages_skipped": 0,
        "pages_failed": 0,
        "pages_with_row_failures": 0,
        "row_failures": 0,
        "files": [],
    }
    summary_path = config.summary_path or (config.output_root / "run_summary.json")
    save_json(summary_path, summary)

    folder_page_map: dict[Path, list[Path]] = {}
    for page_file in page_files:
        folder_page_map.setdefault(page_file.parent, []).append(page_file)

    active_page_files: list[Path] = []
    for folder_dir, folder_page_files in sorted(folder_page_map.items(), key=lambda item: str(item[0])):
        output_folder_dir = config.output_root / folder_dir.relative_to(config.input_root)
        if config.target_page_files is None and config.resume and has_existing_page_files(output_folder_dir):
            logger.warning(
                "[competitor_patent_pipeline] skip enrichment folder because existing page files detected: input_folder={} output_folder={}",
                folder_dir,
                output_folder_dir,
            )
            summary["pages_skipped"] += len(folder_page_files)
            for page_file in folder_page_files:
                output_path = build_enrichment_page_path(config.output_root, config.input_root, page_file)
                summary["files"].append(
                    {
                        "input_file": str(page_file),
                        "output_file": str(output_path),
                        "status": "skipped_existing_output",
                    }
                )
            continue
        active_page_files.extend(folder_page_files)

    save_json(summary_path, summary)
    if not active_page_files:
        return summary_path

    scheduler = RequestScheduler(
        concurrency=max(int(config.request_concurrency), 1),
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
            auth_state = await ensure_enrichment_auth_state(
                config=config,
                managed=managed,
                page_files=active_page_files,
                auth_state=load_auth_state_from_file(config.auth_state_file),
            )

            refresh_count = 0
            for page_file in active_page_files:
                output_path = build_enrichment_page_path(config.output_root, config.input_root, page_file)
                if config.resume and output_path.exists():
                    summary["pages_skipped"] += 1
                    summary["files"].append(
                        {
                            "input_file": str(page_file),
                            "output_file": str(output_path),
                            "status": "skipped_existing_output_file",
                        }
                    )
                    save_json(summary_path, summary)
                    continue

                try:
                    while True:
                        abstract_headers, basic_headers = build_enrichment_request_headers(config, auth_state)
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
                                basic_request_body_template=config.basic_request_body_template,
                                timeout_seconds=config.timeout_seconds,
                                proxies=proxies,
                                scheduler=scheduler,
                                retry_count=config.retry_count,
                                retry_backoff_base_seconds=config.retry_backoff_base_seconds,
                                request_concurrency=config.request_concurrency,
                            )
                            break
                        except AuthRefreshRequiredError:
                            if refresh_count >= config.max_auth_refreshes:
                                raise RuntimeError("auth refresh retry limit reached")
                            refresh_count += 1
                            auth_state = await refresh_auth_state(
                                managed,
                                build_enrichment_auth_refresh_config(config),
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
                            "failure_count": len(supplement_payload["failures"]),
                        }
                    )
                    if supplement_payload["failures"]:
                        summary["pages_with_row_failures"] += 1
                        summary["row_failures"] += len(supplement_payload["failures"])
                except Exception as exc:
                    logger.exception("[competitor_patent_pipeline] enrichment page failed: {}", page_file)
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
    """简介：执行竞争对手专利总流程 task。
    参数：args 为已解析的流程参数。
    返回值：本次运行 summary 文件路径。
    逻辑：当前先完成登录，再抓取竞争对手列表，并输出阶段性 summary。
    """

    from playwright.async_api import async_playwright

    config = build_config(args)
    summary_path = config.pipeline_output_dir / f"competitor_patent_pipeline_{config.month}_summary.json"
    config.pipeline_output_dir.mkdir(parents=True, exist_ok=True)

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
            login_step = await run_step_async(
                ensure_pipeline_logged_in,
                managed,
                config,
                step_name="登录站点并写入 Cookie",
                critical=True,
                retries=DEFAULT_MODULE_STEP_RETRIES,
                retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
            )
            final_url = login_step.value or ""

            mapping_step = await run_step_async(
                fetch_competitor_folder_mapping,
                managed,
                config,
                step_name="抓取并过滤竞争对手文件夹映射",
                critical=True,
                retries=DEFAULT_MODULE_STEP_RETRIES,
                retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
            )
            if mapping_step.value is None:
                raise RuntimeError("failed to fetch competitor folder mapping")
            mapping_path, competitor_count = mapping_step.value

            monthly_step = await run_step_async(
                run_monthly_patent_fetch,
                config=config,
                managed=managed,
                folder_mapping_file=mapping_path,
                auth_config=build_monthly_auth_config(config),
                step_name="按月抓取竞争对手专利",
                critical=True,
                retries=DEFAULT_MODULE_STEP_RETRIES,
                retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
            )
            if monthly_step.value is None:
                raise RuntimeError("failed to fetch monthly patents")
            monthly_summary_path, monthly_summary = monthly_step.value
        finally:
            await managed.close()

    enrich_step = await run_step_async(
        run_existing_output_enrichment,
        build_existing_output_enrichment_config(config),
        step_name="补充专利摘要",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    if enrich_step.value is None:
        raise RuntimeError("failed to enrich monthly patents")
    enrichment_summary_path = enrich_step.value
    translation_summary_path: Path | None = None
    translation_status = "skipped"
    translation_pages_written = 0

    if config.abstract_translation_enabled:
        translation_step = await run_step_async(
            run_translate_patent_abstracts,
            build_patent_abstract_translation_config(config),
            step_name="翻译非中文专利摘要",
            critical=True,
            retries=DEFAULT_MODULE_STEP_RETRIES,
            retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
        )
        if translation_step.value is None:
            raise RuntimeError("failed to translate patent abstracts")
        translation_summary_path = translation_step.value
        translation_status = "done"
        translation_pages_written = load_pages_written(translation_summary_path)

    legal_status_step = await run_step_async(
        refresh_legal_status_mapping_file,
        config=config,
        folder_mapping_file=mapping_path,
        step_name="刷新法律状态映射",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    if legal_status_step.value is None:
        raise RuntimeError("failed to refresh legal status mapping")

    report_step = await run_step_async(
        asyncio.to_thread,
        run_competitor_patent_report,
        build_competitor_patent_report_config(config),
        step_name="生成竞争对手专利月报",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    if report_step.value is None:
        raise RuntimeError("failed to build monthly report")
    report_output_path = report_step.value

    summary_payload = build_pipeline_summary_payload(
        config,
        login_status="done",
        login_final_url=final_url,
        competitor_list_status="done",
        competitor_list_count=competitor_count,
        competitor_list_output=str(mapping_path),
        monthly_patents_status="done",
        monthly_patents_folder_count=len(monthly_summary.get("folders", [])) if isinstance(monthly_summary, dict) else 0,
        monthly_patents_output=str(monthly_summary_path),
        enrich_patents_status="done",
        enrich_patents_output=str(enrichment_summary_path),
        enrich_patents_pages_written=load_pages_written(enrichment_summary_path),
        translate_patents_status=translation_status,
        translate_patents_output=str(translation_summary_path) if translation_summary_path is not None else "",
        translate_patents_pages_written=translation_pages_written,
        build_monthly_report_status="done",
        build_monthly_report_output=str(report_output_path),
    )
    save_json(summary_path, summary_payload)
    logger.info("[competitor_patent_pipeline_task] summary written: {}", summary_path)
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    summary_path = asyncio.run(run_task(args))
    logger.info("[competitor_patent_pipeline_task] done: summary={}", summary_path)


if __name__ == "__main__":
    # 直接执行任务文件时，从这里进入总流程。
    main()

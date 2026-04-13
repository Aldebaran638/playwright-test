import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.common.run_step import run_step_async
from zhy.modules.folder_patents_hybrid import FolderApiTarget, HybridTaskConfig, strip_or_none
from zhy.modules.folder_patents_hybrid.workflow import run_folder_patents_hybrid
from zhy.modules.folder_table.page_url import parse_folder_target


# 默认浏览器可执行文件路径，便于本地直接复用已安装浏览器。
DEFAULT_BROWSER_EXECUTABLE_PATH: str | None = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# 默认用户数据目录，便于复用已有登录态。
DEFAULT_USER_DATA_DIR: str | None = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"

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

# 默认 Cookie 文件路径。
DEFAULT_COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
# 默认鉴权缓存文件路径。
DEFAULT_AUTH_STATE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "folder_patents_auth.json"
# 默认输出根目录。
DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"

# 默认空间 ID。
DEFAULT_SPACE_ID = "ccb6031b05034c7ab2c4b120c2dc3155"
# 默认请求 Origin。
DEFAULT_ORIGIN = "https://workspace.zhihuiya.com"
# 默认请求 Referer。
DEFAULT_REFERER = "https://workspace.zhihuiya.com/"
# 默认站点语言。
DEFAULT_SITE_LANG = "CN"
# 默认 API 版本头。
DEFAULT_API_VERSION = "2.0"
# 默认来源标识头。
DEFAULT_PATSNAP_FROM = "w-analytics-workspace"
# 默认 User-Agent。
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)

DEFAULT_ABSTRACT_REQUEST_URL = "https://search-service.zhihuiya.com/core-search-api/search/translate/patent"
DEFAULT_ABSTRACT_ORIGIN = "https://analytics.zhihuiya.com"
DEFAULT_ABSTRACT_REFERER = "https://analytics.zhihuiya.com/"
DEFAULT_ABSTRACT_X_PATSNAP_FROM = "w-analytics-patent-view"
DEFAULT_ABSTRACT_TEXT_FIELD_NAME = "ABST_TEXT"
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

# 默认起始页。
DEFAULT_START_PAGE = 1
# 默认页级并发数。
DEFAULT_PAGE_CONCURRENCY = 5
# 默认每页条数。
DEFAULT_PAGE_SIZE = 100
# 默认请求超时（秒）。
DEFAULT_TIMEOUT_SECONDS = 30.0
# 默认抓取鉴权监听超时（毫秒）。
DEFAULT_CAPTURE_TIMEOUT_MS = 45000
# 默认最大鉴权刷新次数。
DEFAULT_MAX_AUTH_REFRESHES = 5
# 默认请求重试次数。
DEFAULT_RETRY_COUNT = 3
# 默认重试回退基数（秒）。
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 1.0
# 默认请求最小间隔（秒）。
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.2
# 默认请求抖动上限（秒）。
DEFAULT_REQUEST_JITTER_SECONDS = 0.4

# 默认是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1
# Playwright 原子步骤重试次数。
DEFAULT_PLAYWRIGHT_API_RETRIES = 3
# 模块级步骤重试次数。
DEFAULT_MODULE_STEP_RETRIES = 1
# 步骤级重试等待时间（秒）。
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0

# 默认文件夹 ID 列表，用于快速开发调试。
DEFAULT_FOLDER_IDS: list[str] = [
#   "8614f137547f4e46b8557ae8d3b1e1f5",
#   "306f9f76aa5940a0acfc4b8a4dad8a18",
#   "7e56feab503f4c0fa5103f7e126a8aa0",
#   "7e80a0c91c024d378441f19a3abc5595",
#   "dc7c0f6fd45e43ca967176d99939f828",
#   "0b77a83bc2554d52b66e6350cb8729f3",
#   "55d9e6fa7c5b4cd6998e2209b386c8c6",
#   "f3abc32038024c398b27fbc853ddb205",
#   "01d62c65b6004f12b53dc784a8c7c3db",
#   "5b8f65fdf98f485b9be7fae53b5f6ed6",
#   "dc7b61795b0e47be8962d13b799a21c7",
#   "f2dc68c92d574b1f848f2266033b014a",
#   "b331ddec5e6c49e59164bfe4fa132427",
#   "1144dcc625ed489ebe790ba2e254f93d",
#   "e63beb68be7f462cac8af8fe51a8df2b",
#   "5d4c2efe21fa4d2aa373c45baa5d61d8",
#   "4b40c13a4e3540f2a728c86d2bfbb2a0",
#   "5ec96a5a1736450b8b0c2342e251e102",
#   "3e2addf18de94f06a56580f3b130fba5",
#   "ee6b594b828140f3a68f2cc0f72d361d",
#   "336870f58f784cf4b4c549ce0f89316a",
#   "009169ef5aee4a43bec38f62cc14f4db",
#   "cb0c191101a2433bb624a75f267d42b6",
#   "65f1ca9627d440d7926106e39bb2c594",
#   "9bb085bc5e80483aa74a27f51c913669",
#   "d187d0a086cd4a92a109f80500226124",
#   "d99392d0fe564269b497d84ed4f31d8e",
#   "45cb70936cd24f05bf3f4fb8c3c72966",
#   "cf26fac1e28245b8a66b81d7e64a47ac",
#   "a249554547b34dc5b4ad82850f544085",
#   "1f9454e94df94dd196df0d0988893f7c",
#   "1962c8210697401ea9cc4213cec0101d",
#   "f34307e6b20c49db8f8927d28485cb67",
#   "f784815ff5634edfb8233f09a265ad7a",
#   "d7abe8b21119497491117e971748af4e",
#   "e5cb6f2045dd4851b748d1e2c4fe7b68",
#   "569b56ad2d7d4189a1a6ee5a124b6b04",
#   "310b60921f0c4400ab3c878ea664397a",
#   "8ae33d07b7d14d0baef1eafe1f0422f6",
#   "1044a5104b36448888c1c05a3cda29a9",
#   "5c36f7e6fa46431d91b1e34c833cc448",
#   "f73f14002fe94bd1a6ab8b0ab427230c",
#   "a86a01c2f58d4daa8a0593ae618cab6d",
#   "7ccce16780624173ae5a3efc2ef9d647",
#   "f5dfc19ec04b47b097ed8beaf6388624",
#   "a962bac504ef477396b881710a7eafad",
#   "edb9160ef53e49e09cfd34ff73a45589",
#   "9cfb7e1877c84906b3379d67b9911065",
#   "5c0aefd4596c472e95dc98790174d8b3",
#   "787a7346edaa4ffc8fc7ae7a603eb6d6",
#   "c45b5a8bd9c9437a8dc6d4c4e9bfa105",
#   "750e84c8956f47548185910ef165b8a5",
#   "c08a3139e0d248918e5a8b592b81f22b",
#   "6d408561684845b8b9fd00b625cf700c",
#   "d6f063dcbf0048e1ae71e526e74b3601",
#   "5fc0db0d625444f5a83f9231ac6bec6a",
#   "2e69f3fc17d7480e8e7134ee7af5467d",
#   "718230c735244402baecad348bb0a4bc",
#   "01b43cd9dac749e4af81ee6b5d212d76",
#   "e95ea4564435411c89ef2d41a52d7ca9",
#   "68044c896d0d4ffaaa3ae20a2a675dc8",
#   "75b63248203d4295ad71a909fa34cea7",
#   "580ad81b850848218970071551fc1a08",
#   "33596c1b7b0e445587353da28ac57498",
#   "2b21dce05f16400ea7593772148ee06a",
#   "4c16bd04d3554bd4ac9d590d885c2237",
#   "6caa6b1093fd4615b2606b1203d3baa3",
#   "793859e128104b6e974870666a735dae",
#   "c2061a741c81430583efefc32e9bfd57",
#   "a3acf4cd05484313a17a039be773527b",
#   "a2bab93e765e4a20853444797910912a",
#   "666aaebea71748509859a860665c38ec",
#   "03fbe996aa134fac835bda7b7766c09c",
#   "950a15fe004c4fa9a965216acde42676",
#   "c88509967b154eaa950b0c96573757e9",
#   "5eba3e34aa9b403bbc825a6a72b17fc2",
#   "c8ceee9e288740eaaf18988364cd3d56",
#   "397bd7fc5aad4e458f6a0452a04bf273",
#   "ad4ea54e4f244eee9ac7c0579b18d176",
#   "a069713d31694a7ea80771429593290f",
#   "30eb6fa113d046c984dfde6c82e905fe",
#   "756fc4f5c3344fb5af553d45ff528220",
#   "7d6a0bc6b8e940198c66df6fef83842d",
#   "57124406db7b4ee3915b1c3113e91dcf",
#   "007c18f329fb40d3897d37fa9a82a150",
#   "2300624a77364e3abbd0279bd5c72320",
#   "71a27f3ef8334824a1ffa55a67e619ab",
#   "eb9746f2b28a4832a7711792648bb63b",
#   "fd057347bfeb4aacafbcbbb4ffec399a",
#   "388b79988a4c4e1b86c48e7fca6a3d49",
#   "77d3ebc45ff641769e0ca6867d1c7c98",
#   "22db9b3fbb384ac4a1f127b3b7e70f4b",
#   "df7bf0881b1544a7a5fb0aa5a92cefee",
#   "83004801a39540b9833d5443efbae40d",
#   "da49b4d09d784eb7a43790c17611b861",
#   "526bb38ad5d34f4b88eb957449c2cc2e",
#   "6088f5943a5441b5b48fa96818efc6fe",
#   "4fb8c7db6a454ed88c6493cdafac1911",
#   "0c30e3cdc9a442368a4fb55a24f2505c",
#   "b0b683c182d14e679773e4d1b8ddef8d",
# #   "3d980f6f8f224e72a057292f8735c2ee", 欧莱雅
#   "ecf86655edc0489592233f22e986088a",
#   "0d7b8655db3846b1a21a39dae16f4a59",
#   "1486a184ed5f4d3599b251407aaf54a8"
]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Hybrid folder patents task: capture auth by Playwright and fetch patents data with API pagination."
        )
    )
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--space-id", default=DEFAULT_SPACE_ID)
    parser.add_argument("--folder-id", action="append", dest="folder_ids", default=[])
    parser.add_argument("--folder-url", action="append", dest="folder_urls", default=[])
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_PATH)
    parser.add_argument("--auth-state-file", type=Path, default=DEFAULT_AUTH_STATE_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT_DIR)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--referer", default=DEFAULT_REFERER)
    parser.add_argument("--x-site-lang", default=DEFAULT_SITE_LANG)
    parser.add_argument("--x-api-version", default=DEFAULT_API_VERSION)
    parser.add_argument("--x-patsnap-from", default=DEFAULT_PATSNAP_FROM)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--start-page", type=int, default=DEFAULT_START_PAGE)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--page-concurrency", type=int, default=DEFAULT_PAGE_CONCURRENCY)
    parser.add_argument("--size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--capture-timeout-ms", type=int, default=DEFAULT_CAPTURE_TIMEOUT_MS)
    parser.add_argument("--max-auth-refreshes", type=int, default=DEFAULT_MAX_AUTH_REFRESHES)
    parser.add_argument("--retry-count", type=int, default=DEFAULT_RETRY_COUNT)
    parser.add_argument("--retry-backoff-base-seconds", type=float, default=DEFAULT_RETRY_BACKOFF_BASE_SECONDS)
    parser.add_argument("--min-request-interval-seconds", type=float, default=DEFAULT_MIN_REQUEST_INTERVAL_SECONDS)
    parser.add_argument("--request-jitter-seconds", type=float, default=DEFAULT_REQUEST_JITTER_SECONDS)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--proxy")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    # 当 use-defaults=0 时，保留命令行参数。
    if args.use_defaults == 0:
        return args

    # 当 use-defaults=1 时，统一强制回落到流程文件默认参数。
    args.space_id = DEFAULT_SPACE_ID
    args.folder_ids = list(DEFAULT_FOLDER_IDS)
    args.folder_urls = []
    args.browser_executable_path = DEFAULT_BROWSER_EXECUTABLE_PATH
    args.user_data_dir = DEFAULT_USER_DATA_DIR
    args.cookie_file = DEFAULT_COOKIE_PATH
    args.auth_state_file = DEFAULT_AUTH_STATE_PATH
    args.output_root = DEFAULT_OUTPUT_ROOT_DIR
    args.origin = DEFAULT_ORIGIN
    args.referer = DEFAULT_REFERER
    args.x_site_lang = DEFAULT_SITE_LANG
    args.x_api_version = DEFAULT_API_VERSION
    args.x_patsnap_from = DEFAULT_PATSNAP_FROM
    args.user_agent = DEFAULT_USER_AGENT
    args.start_page = DEFAULT_START_PAGE
    args.max_pages = None
    args.page_concurrency = DEFAULT_PAGE_CONCURRENCY
    args.size = DEFAULT_PAGE_SIZE
    args.timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    args.capture_timeout_ms = DEFAULT_CAPTURE_TIMEOUT_MS
    args.max_auth_refreshes = DEFAULT_MAX_AUTH_REFRESHES
    args.retry_count = DEFAULT_RETRY_COUNT
    args.retry_backoff_base_seconds = DEFAULT_RETRY_BACKOFF_BASE_SECONDS
    args.min_request_interval_seconds = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS
    args.request_jitter_seconds = DEFAULT_REQUEST_JITTER_SECONDS
    args.resume = True
    args.proxy = None
    args.headless = False
    args.fail_fast = False
    return args


async def resolve_folder_targets(args: argparse.Namespace) -> list[FolderApiTarget]:
    """
    简介：解析并去重 folder 目标列表。
    参数：args 为命令行参数对象。
    返回值：FolderApiTarget 列表。
    逻辑：先读取 folder-id，再读取 folder-url，最后在缺省时使用默认列表。
    """

    resolved: list[FolderApiTarget] = []

    # 先处理直接传入的 folder-id。
    for raw_folder_id in args.folder_ids:
        folder_id = strip_or_none(raw_folder_id)
        # 无效空值直接跳过。
        if folder_id:
            resolved.append(FolderApiTarget(space_id=args.space_id, folder_id=folder_id))

    # 再处理 folder-url，解析出 space_id 和 folder_id。
    for folder_url in args.folder_urls:
        target = parse_folder_target(folder_url)
        resolved.append(FolderApiTarget(space_id=target.space_id, folder_id=target.folder_id))

    # 当外部未提供任何目标时，回落到默认文件夹列表。
    if not resolved:
        resolved.extend(
            FolderApiTarget(space_id=args.space_id, folder_id=folder_id)
            for folder_id in DEFAULT_FOLDER_IDS
        )

    deduped: list[FolderApiTarget] = []
    seen: set[tuple[str, str]] = set()

    # 对目标去重，避免重复抓取同一 folder。
    for target in resolved:
        key = (target.space_id, target.folder_id)
        # 已出现过的目标直接跳过。
        if key in seen:
            continue
        deduped.append(target)
        seen.add(key)

    return deduped


def build_hybrid_config(args: argparse.Namespace) -> HybridTaskConfig:
    """把命令行参数转换为模块运行配置对象。"""

    return HybridTaskConfig(
        browser_executable_path=args.browser_executable_path,
        user_data_dir=args.user_data_dir,
        cookie_file=args.cookie_file,
        auth_state_file=args.auth_state_file,
        output_root=args.output_root,
        target_home_url=DEFAULT_TARGET_HOME_URL,
        success_url=DEFAULT_SUCCESS_URL,
        success_header_selector=DEFAULT_SUCCESS_HEADER_SELECTOR,
        success_logged_in_selector=DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
        success_content_selector=DEFAULT_SUCCESS_CONTENT_SELECTOR,
        loading_overlay_selector=DEFAULT_LOADING_OVERLAY_SELECTOR,
        goto_timeout_ms=DEFAULT_GOTO_TIMEOUT_MS,
        login_timeout_seconds=DEFAULT_LOGIN_TIMEOUT_SECONDS,
        login_poll_interval_seconds=DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
        origin=args.origin,
        referer=args.referer,
        x_site_lang=args.x_site_lang,
        x_api_version=args.x_api_version,
        x_patsnap_from=args.x_patsnap_from,
        user_agent=args.user_agent,
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


async def run_task(args: argparse.Namespace) -> Path:
    # 第一步：解析 folder 目标，属于模块级逻辑，使用较少重试。
    target_step = await run_step_async(
        resolve_folder_targets,
        args,
        step_name="解析文件夹目标",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    folder_targets = target_step.value or []

    # 第二步：执行混合抓取主流程，属于模块级逻辑，失败则中止。
    workflow_step = await run_step_async(
        run_folder_patents_hybrid,
        build_hybrid_config(args),
        folder_targets,
        args.space_id,
        step_name="执行混合抓取流程",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )

    summary_path = workflow_step.value
    if summary_path is None:
        raise RuntimeError("hybrid workflow did not return a summary path")
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    summary_path = asyncio.run(run_task(args))
    logger.info("[folder_patents_hybrid_task] done: summary={}", summary_path)


if __name__ == "__main__":
    # 仅在脚本直接运行时触发主流程。
    main()

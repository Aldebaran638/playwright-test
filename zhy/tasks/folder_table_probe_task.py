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
from zhy.modules.common.run_step import run_step_async
from zhy.modules.folder_table.page_url import parse_folder_target
from zhy.modules.folder_table_probe import (
    FolderTableProbeConfig,
    build_page_numbers,
    probe_folder_pages,
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
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=f3abc32038024c398b27fbc853ddb205&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=01d62c65b6004f12b53dc784a8c7c3db&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5b8f65fdf98f485b9be7fae53b5f6ed6&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=dc7b61795b0e47be8962d13b799a21c7&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=f2dc68c92d574b1f848f2266033b014a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=b331ddec5e6c49e59164bfe4fa132427&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=1144dcc625ed489ebe790ba2e254f93d&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=e63beb68be7f462cac8af8fe51a8df2b&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5d4c2efe21fa4d2aa373c45baa5d61d8&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=4b40c13a4e3540f2a728c86d2bfbb2a0&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5ec96a5a1736450b8b0c2342e251e102&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=3e2addf18de94f06a56580f3b130fba5&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=ee6b594b828140f3a68f2cc0f72d361d&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=336870f58f784cf4b4c549ce0f89316a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=009169ef5aee4a43bec38f62cc14f4db&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=cb0c191101a2433bb624a75f267d42b6&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=65f1ca9627d440d7926106e39bb2c594&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=9bb085bc5e80483aa74a27f51c913669&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=d187d0a086cd4a92a109f80500226124&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=d99392d0fe564269b497d84ed4f31d8e&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=45cb70936cd24f05bf3f4fb8c3c72966&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=cf26fac1e28245b8a66b81d7e64a47ac&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=a249554547b34dc5b4ad82850f544085&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=1f9454e94df94dd196df0d0988893f7c&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=1962c8210697401ea9cc4213cec0101d&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=f34307e6b20c49db8f8927d28485cb67&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=f784815ff5634edfb8233f09a265ad7a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=d7abe8b21119497491117e971748af4e&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=e5cb6f2045dd4851b748d1e2c4fe7b68&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=569b56ad2d7d4189a1a6ee5a124b6b04&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=310b60921f0c4400ab3c878ea664397a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=8ae33d07b7d14d0baef1eafe1f0422f6&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=1044a5104b36448888c1c05a3cda29a9&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5c36f7e6fa46431d91b1e34c833cc448&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=f73f14002fe94bd1a6ab8b0ab427230c&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=a86a01c2f58d4daa8a0593ae618cab6d&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=7ccce16780624173ae5a3efc2ef9d647&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=f5dfc19ec04b47b097ed8beaf6388624&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=a962bac504ef477396b881710a7eafad&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=edb9160ef53e49e09cfd34ff73a45589&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=9cfb7e1877c84906b3379d67b9911065&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5c0aefd4596c472e95dc98790174d8b3&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=787a7346edaa4ffc8fc7ae7a603eb6d6&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=c45b5a8bd9c9437a8dc6d4c4e9bfa105&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=750e84c8956f47548185910ef165b8a5&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=c08a3139e0d248918e5a8b592b81f22b&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=6d408561684845b8b9fd00b625cf700c&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=d6f063dcbf0048e1ae71e526e74b3601&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5fc0db0d625444f5a83f9231ac6bec6a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=2e69f3fc17d7480e8e7134ee7af5467d&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=718230c735244402baecad348bb0a4bc&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=01b43cd9dac749e4af81ee6b5d212d76&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=e95ea4564435411c89ef2d41a52d7ca9&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=68044c896d0d4ffaaa3ae20a2a675dc8&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=75b63248203d4295ad71a909fa34cea7&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=580ad81b850848218970071551fc1a08&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=33596c1b7b0e445587353da28ac57498&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=2b21dce05f16400ea7593772148ee06a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=4c16bd04d3554bd4ac9d590d885c2237&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=6caa6b1093fd4615b2606b1203d3baa3&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=793859e128104b6e974870666a735dae&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=c2061a741c81430583efefc32e9bfd57&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=a3acf4cd05484313a17a039be773527b&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=a2bab93e765e4a20853444797910912a&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=666aaebea71748509859a860665c38ec&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=03fbe996aa134fac835bda7b7766c09c&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=950a15fe004c4fa9a965216acde42676&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=c88509967b154eaa950b0c96573757e9&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=5eba3e34aa9b403bbc825a6a72b17fc2&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=c8ceee9e288740eaaf18988364cd3d56&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=397bd7fc5aad4e458f6a0452a04bf273&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=ad4ea54e4f244eee9ac7c0579b18d176&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=a069713d31694a7ea80771429593290f&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=30eb6fa113d046c984dfde6c82e905fe&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=756fc4f5c3344fb5af553d45ff528220&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=7d6a0bc6b8e940198c66df6fef83842d&page=1",
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=57124406db7b4ee3915b1c3113e91dcf&page=1",
]
# 默认单页模式页码。
DEFAULT_PAGE_NUMBER = 1
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
# 当前 task 内直接 Playwright API 调用步骤的默认重试次数。
DEFAULT_PLAYWRIGHT_API_RETRIES = 3
# 当前 task 内模块级步骤的默认重试次数。
DEFAULT_MODULE_STEP_RETRIES = 1
# 当前 task 的重试等待秒数。
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0
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


async def run_module_step(
    step_name: str,
    fn,
    *args,
    critical: bool = True,
    retries: int = DEFAULT_MODULE_STEP_RETRIES,
    **kwargs,
):
    step_result = await run_step_async(
        fn,
        *args,
        step_name=step_name,
        critical=critical,
        retries=retries,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
        **kwargs,
    )
    return step_result.value


async def run_playwright_api_step(
    step_name: str,
    fn,
    *args,
    critical: bool = True,
    retries: int = DEFAULT_PLAYWRIGHT_API_RETRIES,
    **kwargs,
):
    step_result = await run_step_async(
        fn,
        *args,
        step_name=step_name,
        critical=critical,
        retries=retries,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
        **kwargs,
    )
    return step_result.value


async def resolve_folder_target_async(folder_url: str):
    return parse_folder_target(folder_url)


async def close_managed_browser_context_async(managed) -> None:
    await managed.close()


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

    async with async_playwright() as playwright:
        managed = await run_module_step(
            "build_browser_context",
            build_browser_context,
            playwright=playwright,
            user_input=browser_context_user_input,
            headless=runtime_args.headless,
            critical=True,
        )

        try:
            # 先加载已有 Cookie，尽量避免重复登录。
            await run_module_step(
                "load_cookies_if_present",
                load_cookies_if_present,
                managed.context,
                runtime_args.cookie_path,
                critical=False,
            )

            # 当前步骤负责把站点初始化到可进入文件夹表格的状态。
            login_page = await run_module_step(
                "initialize_site",
                initialize_site,
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
                critical=True,
            )
            await run_module_step(
                "save_cookies",
                save_cookies,
                managed.context,
                runtime_args.cookie_path,
                critical=False,
            )
            logger.info("[folder_table_probe_task] site initialization finished at {}", login_page.url)

            # 文件夹之间严格串行执行，避免多个文件夹并发争抢同一浏览器上下文。
            for folder_url in folder_urls:
                target = await run_module_step(
                    "parse_folder_target",
                    resolve_folder_target_async,
                    folder_url,
                    critical=False,
                )
                if target is None:
                    logger.warning("[folder_table_probe_task] skip folder because target parsing failed: {}", folder_url)
                    continue

                # 当前循环只处理一个文件夹，文件夹内部的页码并发交给模块层控制。
                summary = await run_module_step(
                    f"probe_folder_pages:{target.folder_id}",
                    probe_folder_pages,
                    context=managed.context,
                    target=target,
                    config=probe_config,
                    selectors=DEFAULT_SELECTORS,
                    critical=False,
                )
                if summary is None:
                    logger.warning("[folder_table_probe_task] skip folder because probing failed: {}", target.folder_id)
                    continue

                logger.info(
                    "[folder_table_probe_task] folder {} finished: successful_pages={} failed_pages={} total_rows_written={} output_dir={}",
                    summary.folder_id,
                    summary.successful_pages,
                    summary.failed_pages,
                    summary.total_rows_written,
                    summary.output_dir,
                )
        finally:
            await run_playwright_api_step(
                "managed.close",
                close_managed_browser_context_async,
                managed,
                critical=False,
            )


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    asyncio.run(run_probe(args))


if __name__ == "__main__":
    main()
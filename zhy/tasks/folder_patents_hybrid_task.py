import argparse
import asyncio
import copy
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from random import uniform
from time import monotonic
from urllib.parse import urlparse

import requests
from loguru import logger
from playwright.async_api import Request, async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.browser_context.browser_context_workflow import BrowserContextUserInput
from zhy.modules.browser_context.runtime import ManagedBrowserContext, build_browser_context
from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies
from zhy.modules.folder_table.page_url import parse_folder_target
from zhy.modules.site_init.initialize_site_async import initialize_site


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

DEFAULT_COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
DEFAULT_AUTH_STATE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "folder_patents_auth.json"
DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"

DEFAULT_SPACE_ID = "ccb6031b05034c7ab2c4b120c2dc3155"
DEFAULT_ORIGIN = "https://workspace.zhihuiya.com"
DEFAULT_REFERER = "https://workspace.zhihuiya.com/"
DEFAULT_SITE_LANG = "CN"
DEFAULT_API_VERSION = "2.0"
DEFAULT_PATSNAP_FROM = "w-analytics-workspace"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)
DEFAULT_START_PAGE = 1
DEFAULT_PAGE_CONCURRENCY = 5
DEFAULT_PAGE_SIZE = 20
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_CAPTURE_TIMEOUT_MS = 45000
DEFAULT_MAX_AUTH_REFRESHES = 5
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 1.0
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.2
DEFAULT_REQUEST_JITTER_SECONDS = 0.4

DEFAULT_FOLDER_IDS: list[str] = [
    "8614f137547f4e46b8557ae8d3b1e1f5",
    "306f9f76aa5940a0acfc4b8a4dad8a18",
    "7e56feab503f4c0fa5103f7e126a8aa0",
    "7e80a0c91c024d378441f19a3abc5595",
    "dc7c0f6fd45e43ca967176d99939f828",
    "0b77a83bc2554d52b66e6350cb8729f3",
    "55d9e6fa7c5b4cd6998e2209b386c8c6",
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
    "3d980f6f8f224e72a057292f8735c2ee",
    "ecf86655edc0489592233f22e986088a",
    "0d7b8655db3846b1a21a39dae16f4a59",
    "1486a184ed5f4d3599b251407aaf54a8",
]


class AuthRefreshRequiredError(Exception):
    pass


class TransientRequestError(Exception):
    pass


@dataclass
class FolderAuthState:
    space_id: str
    folder_id: str
    request_url: str
    authorization: str | None
    x_client_id: str | None
    x_device_id: str | None
    b3: str | None
    cookie_header: str | None
    body_template: dict
    captured_at: str

    def to_headers(self, args: argparse.Namespace) -> dict[str, str]:
        headers: dict[str, str] = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": args.origin,
            "referer": args.referer,
            "user-agent": args.user_agent,
            "x-api-version": args.x_api_version,
            "x-patsnap-from": args.x_patsnap_from,
            "x-requested-with": "XMLHttpRequest",
            "x-site-lang": args.x_site_lang,
        }
        if self.authorization:
            headers["authorization"] = self.authorization
        if self.x_client_id:
            headers["x-client-id"] = self.x_client_id
        if self.x_device_id:
            headers["x-device-id"] = self.x_device_id
        if self.b3:
            headers["b3"] = self.b3
        if self.cookie_header:
            headers["cookie"] = self.cookie_header
        return headers

    def to_json(self) -> dict:
        return {
            "space_id": self.space_id,
            "folder_id": self.folder_id,
            "request_url": self.request_url,
            "authorization": self.authorization,
            "x_client_id": self.x_client_id,
            "x_device_id": self.x_device_id,
            "b3": self.b3,
            "cookie_header": self.cookie_header,
            "body_template": self.body_template,
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_json(cls, data: dict) -> "FolderAuthState":
        return cls(
            space_id=str(data.get("space_id") or "").strip(),
            folder_id=str(data.get("folder_id") or "").strip(),
            request_url=str(data.get("request_url") or "").strip(),
            authorization=_strip_or_none(data.get("authorization")),
            x_client_id=_strip_or_none(data.get("x_client_id")),
            x_device_id=_strip_or_none(data.get("x_device_id")),
            b3=_strip_or_none(data.get("b3")),
            cookie_header=_strip_or_none(data.get("cookie_header")),
            body_template=data.get("body_template") if isinstance(data.get("body_template"), dict) else {},
            captured_at=str(data.get("captured_at") or "").strip(),
        )


@dataclass(frozen=True)
class FolderApiTarget:
    space_id: str
    folder_id: str


class RequestScheduler:
    def __init__(
        self,
        concurrency: int,
        min_interval_seconds: float,
        jitter_seconds: float,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max(concurrency, 1))
        self._interval_lock = asyncio.Lock()
        self._last_request_started_at = 0.0
        self._min_interval_seconds = max(min_interval_seconds, 0.0)
        self._jitter_seconds = max(jitter_seconds, 0.0)

    async def __aenter__(self):
        await self._semaphore.acquire()
        await self._wait_for_slot()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._semaphore.release()

    async def _wait_for_slot(self) -> None:
        async with self._interval_lock:
            now = monotonic()
            target = self._last_request_started_at + self._min_interval_seconds
            wait_seconds = max(0.0, target - now)
            wait_seconds += uniform(0.0, self._jitter_seconds)
            if wait_seconds > 0:
                logger.debug(
                    "[folder_patents_hybrid_task] scheduler wait: sleep={:.3f}s min_interval={:.3f}s jitter_max={:.3f}s",
                    wait_seconds,
                    self._min_interval_seconds,
                    self._jitter_seconds,
                )
                await asyncio.sleep(wait_seconds)
            self._last_request_started_at = monotonic()


def _strip_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Login with Playwright, capture the real patents API auth headers, "
            "then fetch folder patents with concurrent requests and auto refresh auth on 401."
        )
    )
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
    parser.add_argument(
        "--retry-backoff-base-seconds",
        type=float,
        default=DEFAULT_RETRY_BACKOFF_BASE_SECONDS,
    )
    parser.add_argument(
        "--min-request-interval-seconds",
        type=float,
        default=DEFAULT_MIN_REQUEST_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--request-jitter-seconds",
        type=float,
        default=DEFAULT_REQUEST_JITTER_SECONDS,
    )
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--proxy")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def resolve_folder_targets(args: argparse.Namespace) -> list[FolderApiTarget]:
    resolved: list[FolderApiTarget] = []

    for raw_folder_id in args.folder_ids:
        folder_id = _strip_or_none(raw_folder_id)
        if folder_id:
            resolved.append(FolderApiTarget(space_id=args.space_id, folder_id=folder_id))

    for folder_url in args.folder_urls:
        target = parse_folder_target(folder_url)
        resolved.append(FolderApiTarget(space_id=target.space_id, folder_id=target.folder_id))

    if not resolved:
        resolved.extend(
            FolderApiTarget(space_id=args.space_id, folder_id=folder_id)
            for folder_id in DEFAULT_FOLDER_IDS
        )

    deduped: list[FolderApiTarget] = []
    seen: set[tuple[str, str]] = set()
    for target in resolved:
        key = (target.space_id, target.folder_id)
        if key in seen:
            continue
        deduped.append(target)
        seen.add(key)
    return deduped


def build_folder_page_url(space_id: str, folder_id: str, page: int) -> str:
    return (
        "https://workspace.zhihuiya.com/detail/patent/table"
        f"?spaceId={space_id}&folderId={folder_id}&page={page}"
    )


def build_request_body_for_page(template: dict, space_id: str, folder_id: str, page: int, size: int) -> dict:
    body = copy.deepcopy(template)
    body["space_id"] = space_id
    body["folder_id"] = folder_id
    body["size"] = size
    if isinstance(body.get("page"), int):
        body["page"] = page
    else:
        body["page"] = str(page)
    return body


def build_cookie_header_from_cookie_list(cookies: list[dict]) -> str | None:
    items: list[str] = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name:
            continue
        items.append(f"{name}={value or ''}")
    if not items:
        return None
    return "; ".join(items)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json_file_any_utf(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_auth_state_if_valid(path: Path, expected_space_id: str, expected_folder_id: str) -> FolderAuthState | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    auth_state = FolderAuthState.from_json(raw)
    if auth_state.space_id != expected_space_id or auth_state.folder_id != expected_folder_id:
        return None
    if not auth_state.request_url or not auth_state.body_template:
        return None
    return auth_state


async def ensure_logged_in(
    managed: ManagedBrowserContext,
    args: argparse.Namespace,
) -> None:
    logger.info(
        "[folder_patents_hybrid_task] ensure_logged_in: cookie_file={} target_home={}",
        args.cookie_file,
        DEFAULT_TARGET_HOME_URL,
    )
    await load_cookies_if_present(managed.context, args.cookie_file)
    page = await initialize_site(
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
    await save_cookies(managed.context, args.cookie_file)
    logger.info(
        "[folder_patents_hybrid_task] ensure_logged_in complete: final_url={}",
        page.url,
    )
    await page.close()


def is_matching_patents_request(request: Request, space_id: str, folder_id: str) -> bool:
    if request.method.upper() != "POST":
        return False
    parsed = urlparse(request.url)
    if parsed.netloc != "workspace-service.zhihuiya.com":
        return False
    expected_path = f"/workspace/web/{space_id}/folder/{folder_id}/patents"
    return parsed.path == expected_path


async def capture_patents_auth_state(
    managed: ManagedBrowserContext,
    args: argparse.Namespace,
    space_id: str,
    folder_id: str,
) -> FolderAuthState:
    logger.info(
        "[folder_patents_hybrid_task] capture_auth start: space_id={} folder_id={} start_page={}",
        space_id,
        folder_id,
        args.start_page,
    )
    page = await managed.context.new_page()
    try:
        target_url = build_folder_page_url(space_id, folder_id, args.start_page)

        async def trigger_navigation() -> None:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=args.capture_timeout_ms)

        try:
            async with page.expect_request(
                lambda request: is_matching_patents_request(request, space_id, folder_id),
                timeout=args.capture_timeout_ms,
            ) as request_info:
                await trigger_navigation()
            request = await request_info.value
        except Exception:
            async with page.expect_request(
                lambda request: is_matching_patents_request(request, space_id, folder_id),
                timeout=args.capture_timeout_ms,
            ) as request_info:
                await page.reload(wait_until="domcontentloaded", timeout=args.capture_timeout_ms)
            request = await request_info.value

        headers = await request.all_headers()
        raw_body = request.post_data or "{}"
        try:
            body_template = json.loads(raw_body)
        except json.JSONDecodeError:
            body_template = {}

        cookies = await managed.context.cookies()
        cookie_header = build_cookie_header_from_cookie_list(cookies)
        auth_state = FolderAuthState(
            space_id=space_id,
            folder_id=folder_id,
            request_url=request.url,
            authorization=_strip_or_none(headers.get("authorization")),
            x_client_id=_strip_or_none(headers.get("x-client-id")),
            x_device_id=_strip_or_none(headers.get("x-device-id")),
            b3=_strip_or_none(headers.get("b3")),
            cookie_header=cookie_header,
            body_template=body_template if isinstance(body_template, dict) else {},
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
        save_json(args.auth_state_file, auth_state.to_json())
        await save_cookies(managed.context, args.cookie_file)
        logger.info(
            "[folder_patents_hybrid_task] capture_auth success: folder_id={} request_url={} has_authorization={} has_x_client_id={} has_x_device_id={} has_b3={} has_cookie={}",
            folder_id,
            auth_state.request_url,
            bool(auth_state.authorization),
            bool(auth_state.x_client_id),
            bool(auth_state.x_device_id),
            bool(auth_state.b3),
            bool(auth_state.cookie_header),
        )
        return auth_state
    finally:
        await page.close()


def post_page_sync(
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> dict:
    response = requests.post(
        url,
        headers=headers,
        json=body,
        timeout=timeout_seconds,
        proxies=proxies,
    )
    if response.status_code == 401:
        raise AuthRefreshRequiredError("received 401 from patents API")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise TransientRequestError(f"transient status code: {response.status_code}")
    response.raise_for_status()
    return response.json()


async def post_page_async(
    *,
    page: int,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler: RequestScheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
) -> tuple[int, dict]:
    attempts = max(retry_count, 1)
    for attempt_index in range(attempts):
        try:
            logger.debug(
                "[folder_patents_hybrid_task] request start: page={} attempt={}/{} url={}",
                page,
                attempt_index + 1,
                attempts,
                url,
            )
            async with scheduler:
                parsed = await asyncio.to_thread(
                    post_page_sync,
                    url,
                    headers,
                    body,
                    timeout_seconds,
                    proxies,
                )
            logger.debug(
                "[folder_patents_hybrid_task] request success: page={} attempt={}/{}",
                page,
                attempt_index + 1,
                attempts,
            )
            return page, parsed
        except AuthRefreshRequiredError:
            logger.warning(
                "[folder_patents_hybrid_task] request got 401: page={} attempt={}/{}",
                page,
                attempt_index + 1,
                attempts,
            )
            raise
        except (TransientRequestError, requests.Timeout, requests.ConnectionError) as exc:
            if attempt_index >= attempts - 1:
                logger.error(
                    "[folder_patents_hybrid_task] request exhausted retries: page={} attempts={} error={}",
                    page,
                    attempts,
                    exc,
                )
                raise
            backoff_seconds = retry_backoff_base_seconds * (2**attempt_index)
            logger.warning(
                "[folder_patents_hybrid_task] request retry scheduled: page={} attempt={}/{} error={} sleep={}s",
                page,
                attempt_index + 1,
                attempts,
                exc,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)
        except requests.HTTPError:
            logger.exception(
                "[folder_patents_hybrid_task] request fatal http error: page={} attempt={}/{}",
                page,
                attempt_index + 1,
                attempts,
            )
            raise


def build_output_path(output_root: Path, space_id: str, folder_id: str, page: int) -> Path:
    folder_dir = output_root / f"{space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{page:04d}.json"


async def refresh_auth_state(
    managed: ManagedBrowserContext,
    args: argparse.Namespace,
    space_id: str,
    folder_id: str,
) -> FolderAuthState:
    logger.warning(
        "[folder_patents_hybrid_task] refreshing auth state: space_id={} folder_id={}",
        space_id,
        folder_id,
    )
    await ensure_logged_in(managed, args)
    return await capture_patents_auth_state(managed, args, space_id, folder_id)


async def fetch_folder_patents(
    managed: ManagedBrowserContext,
    args: argparse.Namespace,
    target: FolderApiTarget,
    scheduler: RequestScheduler,
    summary_path: Path,
    run_summary: dict,
) -> dict:
    logger.info(
        "[folder_patents_hybrid_task] folder start: space_id={} folder_id={} start_page={} page_concurrency={} size={} resume={}",
        target.space_id,
        target.folder_id,
        args.start_page,
        args.page_concurrency,
        args.size,
        args.resume,
    )
    auth_state = load_auth_state_if_valid(args.auth_state_file, target.space_id, target.folder_id)
    if auth_state is None:
        logger.info(
            "[folder_patents_hybrid_task] auth_state cache miss: folder_id={} auth_state_file={}",
            target.folder_id,
            args.auth_state_file,
        )
        auth_state = await refresh_auth_state(managed, args, target.space_id, target.folder_id)
    else:
        logger.info(
            "[folder_patents_hybrid_task] auth_state cache hit: folder_id={} captured_at={} request_url={}",
            target.folder_id,
            auth_state.captured_at,
            auth_state.request_url,
        )

    folder_summary = {
        "space_id": target.space_id,
        "folder_id": target.folder_id,
        "status": "ok",
        "reason": "",
        "total": None,
        "limit": None,
        "pages_saved": 0,
        "last_page_requested": None,
        "last_page_patent_count": None,
        "saved_files": [],
        "error": None,
        "auth_refresh_count": 0,
    }

    request_url = auth_state.request_url or (
        "https://workspace-service.zhihuiya.com/"
        f"workspace/web/{target.space_id}/folder/{target.folder_id}/patents"
    )
    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
    next_page = args.start_page

    while True:
        if args.max_pages is not None:
            remaining = args.max_pages - folder_summary["pages_saved"]
            if remaining <= 0:
                folder_summary["reason"] = "reached_max_pages_limit"
                logger.info(
                    "[folder_patents_hybrid_task] folder stop: folder_id={} reason={} pages_saved={}",
                    target.folder_id,
                    folder_summary["reason"],
                    folder_summary["pages_saved"],
                )
                break
            batch_size = min(args.page_concurrency, remaining)
        else:
            batch_size = args.page_concurrency

        pages = list(range(next_page, next_page + batch_size))
        logger.info(
            "[folder_patents_hybrid_task] batch start: folder_id={} pages={} request_url={}",
            target.folder_id,
            pages,
            request_url,
        )
        headers = auth_state.to_headers(args)
        tasks = []
        for page_number in pages:
            output_path = build_output_path(args.output_root, target.space_id, target.folder_id, page_number)
            if args.resume and output_path.exists():
                try:
                    parsed = load_json_file_any_utf(output_path)
                    logger.info(
                        "[folder_patents_hybrid_task] resume hit: folder_id={} page={} file={}",
                        target.folder_id,
                        page_number,
                        output_path,
                    )
                    tasks.append(asyncio.create_task(asyncio.sleep(0, result=(page_number, parsed))))
                    continue
                except Exception:
                    logger.warning(
                        "[folder_patents_hybrid_task] resume read failed, refetch page file {}",
                        output_path,
                    )
            body = build_request_body_for_page(
                auth_state.body_template,
                target.space_id,
                target.folder_id,
                page_number,
                args.size,
            )
            tasks.append(
                asyncio.create_task(
                    post_page_async(
                        page=page_number,
                        url=request_url,
                        headers=headers,
                        body=body,
                        timeout_seconds=args.timeout_seconds,
                        proxies=proxies,
                        scheduler=scheduler,
                        retry_count=args.retry_count,
                        retry_backoff_base_seconds=args.retry_backoff_base_seconds,
                    )
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        auth_error = next((item for item in results if isinstance(item, AuthRefreshRequiredError)), None)
        if auth_error is not None:
            if folder_summary["auth_refresh_count"] >= args.max_auth_refreshes:
                raise RuntimeError("auth refresh retry limit reached") from auth_error
            folder_summary["auth_refresh_count"] += 1
            logger.warning(
                "[folder_patents_hybrid_task] auth refresh triggered by 401: folder_id={} auth_refresh_count={}/{}",
                target.folder_id,
                folder_summary["auth_refresh_count"],
                args.max_auth_refreshes,
            )
            auth_state = await refresh_auth_state(managed, args, target.space_id, target.folder_id)
            continue

        for item in results:
            if isinstance(item, Exception):
                logger.exception(
                    "[folder_patents_hybrid_task] batch failure: folder_id={} next_page={} error={}",
                    target.folder_id,
                    next_page,
                    item,
                )
                raise item

        batch_results = sorted(results, key=lambda item: item[0])
        should_stop_folder = False
        for page_number, parsed in batch_results:
            output_path = build_output_path(args.output_root, target.space_id, target.folder_id, page_number)
            save_json(output_path, parsed)

            folder_summary["saved_files"].append(str(output_path))
            folder_summary["pages_saved"] += 1
            folder_summary["last_page_requested"] = page_number

            data = parsed.get("data") if isinstance(parsed, dict) else None
            if not isinstance(data, dict):
                folder_summary["reason"] = "missing_data_object"
                logger.error(
                    "[folder_patents_hybrid_task] page invalid: folder_id={} page={} reason={}",
                    target.folder_id,
                    page_number,
                    folder_summary["reason"],
                )
                should_stop_folder = True
                break

            patents_data = data.get("patents_data")
            patent_count = len(patents_data) if isinstance(patents_data, list) else 0
            folder_summary["last_page_patent_count"] = patent_count

            total = data.get("total")
            limit = data.get("limit")
            try:
                total_int = int(total) if total is not None else None
            except (TypeError, ValueError):
                total_int = None
            try:
                limit_int = int(limit) if limit is not None else None
            except (TypeError, ValueError):
                limit_int = None

            folder_summary["total"] = total_int
            folder_summary["limit"] = limit_int
            logger.info(
                "[folder_patents_hybrid_task] page saved: folder_id={} page={} patent_count={} total={} limit={} file={}",
                target.folder_id,
                page_number,
                patent_count,
                total_int,
                limit_int,
                output_path,
            )

            if patent_count == 0:
                folder_summary["reason"] = "empty_page_detected"
                logger.info(
                    "[folder_patents_hybrid_task] folder stop: folder_id={} page={} reason={}",
                    target.folder_id,
                    page_number,
                    folder_summary["reason"],
                )
                should_stop_folder = True
                break

            if total_int is not None and limit_int and limit_int > 0:
                max_page_by_total = math.ceil(total_int / limit_int)
                if page_number >= max_page_by_total:
                    folder_summary["reason"] = "reached_total_page"
                    logger.info(
                        "[folder_patents_hybrid_task] folder stop: folder_id={} page={} reason={} max_page_by_total={}",
                        target.folder_id,
                        page_number,
                        folder_summary["reason"],
                        max_page_by_total,
                    )
                    should_stop_folder = True
                    break

        if should_stop_folder:
            break

        next_page += batch_size
        logger.info(
            "[folder_patents_hybrid_task] batch complete: folder_id={} next_page={} pages_saved={}",
            target.folder_id,
            next_page,
            folder_summary["pages_saved"],
        )

    logger.info(
        "[folder_patents_hybrid_task] folder end: folder_id={} status={} reason={} pages_saved={} last_page_requested={} auth_refresh_count={}",
        target.folder_id,
        folder_summary["status"],
        folder_summary["reason"],
        folder_summary["pages_saved"],
        folder_summary["last_page_requested"],
        folder_summary["auth_refresh_count"],
    )
    return folder_summary


async def run_hybrid_task(args: argparse.Namespace) -> Path:
    folder_targets = resolve_folder_targets(args)
    if not folder_targets:
        raise ValueError("no folder targets resolved")
    if args.page_concurrency <= 0:
        raise ValueError("page_concurrency must be greater than 0")
    if args.size <= 0:
        raise ValueError("size must be greater than 0")

    run_summary = {
        "default_space_id": args.space_id,
        "folders": [],
    }
    summary_path = args.output_root / f"{args.space_id}_run_summary.json"
    save_json(summary_path, run_summary)
    logger.info(
        "[folder_patents_hybrid_task] run start: folder_count={} summary_path={} output_root={} auth_state_file={} page_concurrency={} retry_count={} min_request_interval_seconds={} jitter_seconds={} resume={}",
        len(folder_targets),
        summary_path,
        args.output_root,
        args.auth_state_file,
        args.page_concurrency,
        args.retry_count,
        args.min_request_interval_seconds,
        args.request_jitter_seconds,
        args.resume,
    )

    browser_input = BrowserContextUserInput(
        browser_executable_path=args.browser_executable_path,
        user_data_dir=args.user_data_dir,
    )
    scheduler = RequestScheduler(
        concurrency=args.page_concurrency,
        min_interval_seconds=args.min_request_interval_seconds,
        jitter_seconds=args.request_jitter_seconds,
    )

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=browser_input,
            headless=args.headless,
        )
        try:
            await ensure_logged_in(managed, args)

            for target in folder_targets:
                try:
                    summary = await fetch_folder_patents(
                        managed,
                        args,
                        target,
                        scheduler,
                        summary_path,
                        run_summary,
                    )
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
                    }
                    logger.exception(
                        "[folder_patents_hybrid_task] folder {} failed: {}",
                        target.folder_id,
                        exc,
                    )
                    run_summary["folders"].append(summary)
                    save_json(summary_path, run_summary)
                    if args.fail_fast:
                        break
                    continue

                run_summary["folders"].append(summary)
                save_json(summary_path, run_summary)
                logger.info(
                    "[folder_patents_hybrid_task] folder {} finished: pages_saved={} auth_refresh_count={} reason={}",
                    target.folder_id,
                    summary["pages_saved"],
                    summary["auth_refresh_count"],
                    summary["reason"],
                )
        finally:
            await managed.close()

    save_json(summary_path, run_summary)
    logger.info(
        "[folder_patents_hybrid_task] run end: folder_count={} summary_path={}",
        len(run_summary["folders"]),
        summary_path,
    )
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    summary_path = asyncio.run(run_hybrid_task(args))
    logger.info("[folder_patents_hybrid_task] done: summary={}", summary_path)


if __name__ == "__main__":
    main()

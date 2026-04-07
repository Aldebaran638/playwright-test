import time

from loguru import logger
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError


TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
SUCCESS_HEADER_SELECTOR = "#header-wrapper"
SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0


def normalize_url(url: str) -> str:
    return (url or "").strip()


def selector_exists(page: Page, selector: str) -> bool:
    # 只判断节点是否存在，适合用来判断页面结构是否已经渲染。
    try:
        return page.locator(selector).count() > 0
    except Exception:
        return False


def selector_is_visible(page: Page, selector: str) -> bool:
    # 用可见性判断页面是否仍在预加载，避免只靠节点存在导致误判。
    try:
        locator = page.locator(selector)
        if locator.count() == 0:
            return False
        return locator.first.is_visible()
    except Exception:
        return False


# 判断当前页面是否已经满足“登录成功且页面主体完成加载”的条件。
# 参数：
# - page: 当前正在检测的 Playwright 页面对象。
# - success_url: 用户确认的登录成功目标地址。
# 返回：
# - 只有当 URL、头部、已登录用户中心和主体内容同时成立，且预加载层不可见时，才返回 True。
def has_reached_logged_in_state(
    page: Page,
    success_url: str = TARGET_HOME_URL,
) -> bool:
    current_url = normalize_url(page.url)
    target_url = normalize_url(success_url)
    if current_url != target_url:
        return False

    if not selector_exists(page, SUCCESS_HEADER_SELECTOR):
        return False
    if not selector_exists(page, SUCCESS_LOGGED_IN_SELECTOR):
        return False
    if not selector_exists(page, SUCCESS_CONTENT_SELECTOR):
        return False
    if selector_is_visible(page, LOADING_OVERLAY_SELECTOR):
        return False

    return True


# 在人工登录场景下轮询等待，直到页面满足稳定的登录成功条件。
# 参数：
# - page: 需要持续检测登录状态的页面对象。
# - success_url: 用户定义的登录成功地址。
# - timeout_seconds: 最长等待时间，默认 10 分钟。
# - poll_interval_seconds: 轮询间隔，默认 3 秒。
# 返回：
# - 登录成功后的同一个页面对象。
def wait_until_login_success(
    page: Page,
    success_url: str = TARGET_HOME_URL,
    timeout_seconds: float = DEFAULT_LOGIN_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
) -> Page:
    deadline = time.time() + timeout_seconds
    target_url = normalize_url(success_url)
    logger.info("[site_init] 开始等待用户手动登录，目标地址：{}", target_url)

    while time.time() < deadline:
        current_url = normalize_url(page.url)
        if has_reached_logged_in_state(page, target_url):
            logger.info("[site_init] 已检测到登录成功且主体内容已加载，当前地址：{}", current_url)
            return page

        logger.info(
            "[site_init] 尚未检测到稳定登录状态，当前地址：{}，{} 秒后继续检查",
            current_url or "<empty>",
            poll_interval_seconds,
        )
        page.wait_for_timeout(poll_interval_seconds * 1000)

    current_url = normalize_url(page.url)
    raise TimeoutError(
        "等待用户登录超时，"
        f"目标地址={target_url}，"
        f"当前地址={current_url or '<empty>'}"
    )


# 基于已有浏览器上下文完成网站初始化，并返回可继续业务操作的页面对象。
# 参数：
# - context: 上一阶段“浏览器上下文初始化”已经创建好的 Playwright BrowserContext。
# 返回：
# - 已完成网站初始化的页面对象。
def initialize_site(context: BrowserContext) -> Page:
    logger.info("[site_init] 开始初始化站点页面")
    page = context.new_page()

    try:
        page.goto(TARGET_HOME_URL, wait_until="domcontentloaded", timeout=30000)
    except PlaywrightTimeoutError:
        # 人工登录场景可能发生重定向或停留在登录页，这里允许继续进入轮询检测阶段。
        logger.warning("[site_init] 打开首页时发生超时，将继续进入登录状态轮询")

    return wait_until_login_success(page)

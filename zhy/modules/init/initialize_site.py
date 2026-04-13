import time

from loguru import logger
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError


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


def has_reached_logged_in_state(
    page: Page,
    success_url: str,
    success_header_selector: str,
    success_logged_in_selector: str,
    success_content_selector: str,
    loading_overlay_selector: str,
) -> bool:
    # 只有 URL、已登录头部、主内容都满足，且预加载层不可见时，才算登录成功。
    current_url = normalize_url(page.url)
    target_url = normalize_url(success_url)
    if current_url != target_url:
        return False

    if not selector_exists(page, success_header_selector):
        return False
    if not selector_exists(page, success_logged_in_selector):
        return False
    if not selector_exists(page, success_content_selector):
        return False
    if selector_is_visible(page, loading_overlay_selector):
        return False

    return True


def wait_until_login_success(
    page: Page,
    success_url: str,
    success_header_selector: str,
    success_logged_in_selector: str,
    success_content_selector: str,
    loading_overlay_selector: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> Page:
    # 轮询等待用户手动登录，直到满足稳定的成功判定。
    deadline = time.time() + timeout_seconds
    target_url = normalize_url(success_url)
    logger.info("[site_init] start waiting for manual login, target url={}", target_url)

    while time.time() < deadline:
        current_url = normalize_url(page.url)
        if has_reached_logged_in_state(
            page=page,
            success_url=target_url,
            success_header_selector=success_header_selector,
            success_logged_in_selector=success_logged_in_selector,
            success_content_selector=success_content_selector,
            loading_overlay_selector=loading_overlay_selector,
        ):
            logger.info("[site_init] login success detected, current url={}", current_url)
            return page

        logger.info(
            "[site_init] login not ready yet, current url={}, check again in {} seconds",
            current_url or "<empty>",
            poll_interval_seconds,
        )
        page.wait_for_timeout(poll_interval_seconds * 1000)

    current_url = normalize_url(page.url)
    raise TimeoutError(
        "waiting for manual login timed out: "
        f"target_url={target_url}, current_url={current_url or '<empty>'}"
    )


def initialize_site(
    context: BrowserContext,
    target_home_url: str,
    success_url: str,
    success_header_selector: str,
    success_logged_in_selector: str,
    success_content_selector: str,
    loading_overlay_selector: str,
    goto_timeout_ms: int,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> Page:
    # 基于已有 context 完成网站初始化，并返回可继续业务操作的页面对象。
    logger.info("[site_init] start site initialization")
    page = context.new_page()

    try:
        page.goto(target_home_url, wait_until="domcontentloaded", timeout=goto_timeout_ms)
    except PlaywrightTimeoutError:
        # 人工登录场景可能停留在登录页或发生重定向，这里允许继续进入轮询阶段。
        logger.warning("[site_init] opening target page timed out, continue waiting for login")

    return wait_until_login_success(
        page=page,
        success_url=success_url,
        success_header_selector=success_header_selector,
        success_logged_in_selector=success_logged_in_selector,
        success_content_selector=success_content_selector,
        loading_overlay_selector=loading_overlay_selector,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )

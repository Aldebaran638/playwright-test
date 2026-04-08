import time

from loguru import logger
from playwright.async_api import BrowserContext, Page


async def selector_exists(page: Page, selector: str) -> bool:
    try:
        return await page.locator(selector).count() > 0
    except Exception:
        return False


async def selector_is_visible(page: Page, selector: str) -> bool:
    try:
        locator = page.locator(selector)
        if await locator.count() == 0:
            return False
        return await locator.first.is_visible()
    except Exception:
        return False


async def has_reached_logged_in_state(
    page: Page,
    success_url: str,
    success_header_selector: str,
    success_logged_in_selector: str,
    success_content_selector: str,
    loading_overlay_selector: str,
) -> bool:
    if page.url.strip() != success_url:
        return False
    if not await selector_exists(page, success_header_selector):
        return False
    if not await selector_exists(page, success_logged_in_selector):
        return False
    if not await selector_exists(page, success_content_selector):
        return False
    if await selector_is_visible(page, loading_overlay_selector):
        return False
    return True


# 简介：在异步 Playwright 上下文中完成站点初始化并等待登录成功。
# 参数：
# - context: 浏览器上下文。
# - target_home_url: 目标首页地址。
# - success_url: 登录成功后应到达的 URL。
# - success_header_selector: 页面头部成功标记选择器。
# - success_logged_in_selector: 已登录状态标记选择器。
# - success_content_selector: 主内容成功标记选择器。
# - loading_overlay_selector: 预加载遮罩选择器。
# - goto_timeout_ms: 打开目标页超时毫秒数。
# - timeout_seconds: 最长等待登录成功的秒数。
# - poll_interval_seconds: 轮询检查间隔秒数。
# 返回值：
# - 登录成功后的页面对象。
# 逻辑：
# - 先尝试打开目标首页，再循环检查登录成功状态，直到成功或超时。
async def initialize_site(
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
    page = await context.new_page()
    try:
        await page.goto(target_home_url, wait_until="domcontentloaded", timeout=goto_timeout_ms)
    except Exception:
        logger.warning("[site_init_async] opening home page timed out, continue waiting for login")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if await has_reached_logged_in_state(
            page=page,
            success_url=success_url,
            success_header_selector=success_header_selector,
            success_logged_in_selector=success_logged_in_selector,
            success_content_selector=success_content_selector,
            loading_overlay_selector=loading_overlay_selector,
        ):
            logger.info("[site_init_async] login success detected")
            return page

        logger.info(
            "[site_init_async] login not ready yet, check again in {} seconds",
            poll_interval_seconds,
        )
        await page.wait_for_timeout(poll_interval_seconds * 1000)

    raise TimeoutError("waiting for manual login timed out")
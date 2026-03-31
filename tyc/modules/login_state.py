import re

from loguru import logger
from playwright.sync_api import Page


LOGGED_IN = 1
LOGGED_OUT = 0
UNKNOWN = -1
CHECK_INTERVAL_MS = 3000

LOGGED_IN_SELECTOR = ".tyc-nav-user-dropdown-label.tyc-header-nav-link"
LOGGED_OUT_SELECTOR = ".tyc-nav-user-btn"


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def get_login_state(page: Page) -> int:
    logged_in_locator = page.locator(LOGGED_IN_SELECTOR)
    if logged_in_locator.count() > 0:
        logged_in_text = normalize_text(logged_in_locator.first.inner_text())
        if logged_in_text:
            return LOGGED_IN

    logged_out_locator = page.locator(LOGGED_OUT_SELECTOR)
    if logged_out_locator.count() > 0:
        logged_out_text = normalize_text(logged_out_locator.first.inner_text())
        if not logged_out_text:
            return LOGGED_OUT
        if "登录" in logged_out_text or "注册" in logged_out_text:
            return LOGGED_OUT
        if "鐧诲綍" in logged_out_text or "娉ㄥ唽" in logged_out_text:
            return LOGGED_OUT
        return LOGGED_OUT

    return UNKNOWN


def wait_until_logged_in(page: Page) -> None:
    logger.info("[login_state] 开始检查当前页面的登录状态")

    while True:
        current_state = get_login_state(page)

        # 已登录时立即结束阻塞，交还主流程继续执行。
        if current_state == LOGGED_IN:
            logger.info("[login_state] 已检测到登录完成，继续执行后续流程")
            return

        # 未登录时提醒用户手动登录，未知状态时继续轮询观察。
        if current_state == LOGGED_OUT:
            logger.warning("[login_state] 当前未登录，请在浏览器中完成登录，系统会每 3 秒复查一次")
        else:
            logger.warning("[login_state] 暂未识别出明确登录状态，系统会每 3 秒继续检查一次")

        page.wait_for_timeout(CHECK_INTERVAL_MS)

from __future__ import annotations

import re

from loguru import logger
from playwright.async_api import Page


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


async def get_login_state_async(page: Page) -> int:
    logged_in_locator = page.locator(LOGGED_IN_SELECTOR)
    if await logged_in_locator.count() > 0:
        logged_in_text = normalize_text(await logged_in_locator.first.inner_text())
        if logged_in_text:
            return LOGGED_IN

    logged_out_locator = page.locator(LOGGED_OUT_SELECTOR)
    if await logged_out_locator.count() > 0:
        logged_out_text = normalize_text(await logged_out_locator.first.inner_text())
        if not logged_out_text:
            return LOGGED_OUT
        if "登录" in logged_out_text or "注册" in logged_out_text:
            return LOGGED_OUT
        if "鐧诲綍" in logged_out_text or "娉ㄥ唽" in logged_out_text:
            return LOGGED_OUT
        return LOGGED_OUT

    return UNKNOWN


async def wait_until_logged_in_async(page: Page) -> None:
    logger.info("[login_state_async] 开始检查当前页面的登录状态")

    while True:
        current_state = await get_login_state_async(page)
        if current_state == LOGGED_IN:
            logger.info("[login_state_async] 已检测到登录完成，继续执行后续流程")
            return

        if current_state == LOGGED_OUT:
            logger.warning("[login_state_async] 当前未登录，请在浏览器中完成登录，系统会每 3 秒复查一次")
        else:
            logger.warning("[login_state_async] 暂未识别出明确登录状态，系统会每 3 秒继续检查一次")

        await page.wait_for_timeout(CHECK_INTERVAL_MS)
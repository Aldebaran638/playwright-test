import re

from loguru import logger
from playwright.sync_api import Page


VERIFICATION_TEXT_PATTERNS = [
    "请进行身份验证以继续使用",
    "身份验证",
    "继续使用",
]

VERIFICATION_SELECTOR_PATTERNS = [
    ".geetest_captcha",
    ".geetest_popup_wrap",
    "#captcha",
]


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    if not isinstance(value, str):
        return str(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def is_verification_page(page: Page) -> bool:
    # 优先通过正文提示词识别身份验证页。
    body = page.locator("body")
    body_text = ""
    if body.count() > 0:
        body_text = normalize_text(body.first.inner_text())

    if any(pattern in body_text for pattern in VERIFICATION_TEXT_PATTERNS):
        logger.info("[模块] 检测到身份验证页面提示词")
        return True

    # 如果正文提示词不明显，再通过验证码容器兜底识别。
    for selector in VERIFICATION_SELECTOR_PATTERNS:
        if page.locator(selector).count() > 0:
            logger.info(f"[模块] 检测到身份验证页面特征选择器: {selector}")
            return True

    return False

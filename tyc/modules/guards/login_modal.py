import re

from loguru import logger
from playwright.sync_api import Page


LOGIN_MODAL_TEXT_PATTERNS = [
    "扫码登录",
    "登录即表示同意",
    "用户协议",
    "隐私政策",
]

LOGIN_MODAL_SELECTOR_PATTERNS = [
    "div[role='dialog'].tyc-modal",
    ".login-main",
    ".login-scan",
    ".qrcode-wrapper",
]


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def is_login_modal_page(page: Page) -> bool:
    # 优先通过登录弹窗中的关键文案识别中途弹出的登录界面。
    body = page.locator("body")
    body_text = ""
    if body.count() > 0:
        body_text = normalize_text(body.first.inner_text())

    if all(pattern in body_text for pattern in LOGIN_MODAL_TEXT_PATTERNS):
        logger.info("[模块] 检测到登录弹窗提示文案")
        return True

    # 如果关键文案不完整，再通过登录弹窗结构选择器兜底识别。
    matched_selectors = 0
    for selector in LOGIN_MODAL_SELECTOR_PATTERNS:
        if page.locator(selector).count() > 0:
            matched_selectors += 1

    if matched_selectors >= 2:
        logger.info("[模块] 检测到登录弹窗结构特征")
        return True

    return False

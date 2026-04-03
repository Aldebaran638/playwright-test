from dataclasses import dataclass

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.guards.login_modal import is_login_modal_page
from tyc.modules.guards.verification_page import is_verification_page


NORMAL_PAGE = "normal_page"
LOGIN_MODAL_PAGE = "login_modal_page"
VERIFICATION_PAGE = "verification_page"


@dataclass(frozen=True, slots=True)
class PageGuardResult:
    is_illegal: bool
    page_type: str
    message: str


def check_page(page: Page) -> PageGuardResult:
    # 先识别登录弹窗，再识别身份验证页，最后才认为当前页面正常。
    if is_login_modal_page(page):
        logger.info("[page_guard] 当前页面被识别为登录弹窗")
        return PageGuardResult(
            is_illegal=True,
            page_type=LOGIN_MODAL_PAGE,
            message="当前页面出现登录弹窗，需要用户手动完成登录。",
        )

    if is_verification_page(page):
        logger.info("[page_guard] 当前页面被识别为身份验证页")
        return PageGuardResult(
            is_illegal=True,
            page_type=VERIFICATION_PAGE,
            message="当前页面是身份验证页，需要用户手动完成验证。",
        )

    logger.info("[page_guard] 当前页面正常")
    return PageGuardResult(
        is_illegal=False,
        page_type=NORMAL_PAGE,
        message="当前页面正常。",
    )

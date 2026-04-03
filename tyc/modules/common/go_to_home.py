from loguru import logger
from playwright.sync_api import Page

from tyc.modules.common.page_guard import check_page
from tyc.modules.common.run_step import run_step
from tyc.modules.common.wait_for_recovery import wait_until_page_recovered


TYC_HOME_URL = "https://www.tianyancha.com/"


def _wait_if_page_blocked(page: Page) -> None:
    guard_result = check_page(page)
    if not guard_result.is_illegal:
        return

    logger.warning(
        f"[go_to_home] 导航首页前检测到异常页面: {guard_result.page_type}，先等待人工处理"
    )
    wait_until_page_recovered(lambda: page)


def go_to_home_page(page: Page, *, home_url: str = TYC_HOME_URL) -> None:
    logger.info(f"[go_to_home] 开始回到首页: {home_url}")
    _wait_if_page_blocked(page)

    run_step(
        page.goto,
        home_url,
        wait_until="domcontentloaded",
        step_name="打开天眼查首页",
        critical=True,
        retries=2,
    )
    logger.info("[go_to_home] 已回到首页")

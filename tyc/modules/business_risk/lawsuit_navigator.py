from loguru import logger
from playwright.sync_api import Page

from tyc.modules.common.page_guard import check_page
from tyc.modules.common.run_step import run_step
from tyc.modules.common.wait_for_recovery import wait_until_page_recovered


def _wait_if_page_blocked(page: Page) -> None:
    guard_result = check_page(page)
    if not guard_result.is_illegal:
        return

    logger.warning(
        f"[business_risk.lawsuit_navigator] 点击法律诉讼标签前检测到异常页面: {guard_result.page_type}，先等待人工处理"
    )
    wait_until_page_recovered(lambda: page)


def click_lawsuit_tab(page: Page) -> None:
    logger.info("[business_risk.lawsuit_navigator] 开始点击法律诉讼标签")
    _wait_if_page_blocked(page)

    run_step(
        page.get_by_text("法律诉讼", exact=False).first.click,
        step_name="点击法律诉讼标签",
        critical=True,
        retries=2,
    )
    logger.info("[business_risk.lawsuit_navigator] 法律诉讼标签点击成功")

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.run_step import run_step


HOME_SEARCH_AREA_SELECTOR = "main section"
HOME_SEARCH_INPUT_SELECTOR = "input[type='text']"


def enter_company_detail_page(page: Page, company_name: str) -> Page:
    # 统一封装从天眼查主页进入指定公司详情页的流程。
    logger.info(f"[模块] 开始搜索公司并进入详情页: {company_name}")

    # 主页里有多个搜索区，优先绑定 main 下的主搜索区域，避免误点吸顶搜索框。
    search_area = page.locator(HOME_SEARCH_AREA_SELECTOR).first
    searchbox = search_area.locator(HOME_SEARCH_INPUT_SELECTOR).first
    search_button = search_area.get_by_role("button").first

    run_step(lambda: searchbox.click(), "点击主搜索区输入框", page_getter=lambda: page)
    run_step(lambda: searchbox.fill(company_name), "输入公司名称", page_getter=lambda: page)
    logger.info(f"[模块] 已输入公司名称: {company_name}")

    run_step(lambda: search_button.click(), "点击主搜索区搜索按钮", page_getter=lambda: page)
    logger.info("[模块] 已点击搜索按钮")

    def open_detail_popup() -> Page:
        with page.expect_popup() as popup_info:
            page.get_by_role("link", name=company_name, exact=True).click()
        return popup_info.value

    detail_page = run_step(
        open_detail_popup,
        "点击公司详情链接并等待新详情页打开",
        page_getter=lambda: page,
    )
    logger.info(f"[模块] 已打开公司详情页: {company_name}")
    return detail_page

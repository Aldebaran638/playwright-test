from loguru import logger
from playwright.sync_api import Page

from tyc.modules.common.page_guard import check_page
from tyc.modules.common.run_step import run_step
from tyc.modules.common.wait_for_recovery import wait_until_page_recovered


HOME_SEARCH_AREA_SELECTOR = "main section"
HOME_SEARCH_INPUT_SELECTOR = "input[type='text']"


def _wait_if_page_blocked(page: Page, *, stage_name: str) -> None:
    guard_result = check_page(page)
    if not guard_result.is_illegal:
        return

    logger.warning(
        f"[enter_company_detail_page] {stage_name} 前检测到异常页面: {guard_result.page_type}，先等待人工处理"
    )
    wait_until_page_recovered(lambda: page)


def _normalize_company_name(name: str) -> str:
    """标准化公司名称，将中英文括号视为相同"""
    # 将中文括号替换为英文括号
    return name.replace("（", "(").replace("）", ")")


def enter_company_detail_page(page: Page, company_name: str) -> Page:
    logger.info(f"[enter_company_detail_page] 开始搜索公司并进入详情页: {company_name}")
    _wait_if_page_blocked(page, stage_name="进入公司详情页")

    # 优先绑定主页主搜索区，避免误点顶部吸附搜索框。
    search_area = page.locator(HOME_SEARCH_AREA_SELECTOR).first
    searchbox = search_area.locator(HOME_SEARCH_INPUT_SELECTOR).first
    search_button = search_area.get_by_role("button").first

    run_step(
        searchbox.click,
        step_name="点击主搜索区输入框",
        critical=True,
        retries=2,
    )
    run_step(
        searchbox.fill,
        company_name,
        step_name="输入公司名称",
        critical=True,
        retries=1,
    )
    logger.info(f"[enter_company_detail_page] 已输入公司名称: {company_name}")

    run_step(
        search_button.click,
        step_name="点击主搜索区搜索按钮",
        critical=True,
        retries=2,
    )
    logger.info("[enter_company_detail_page] 已点击搜索按钮")

    def open_detail_popup() -> Page:
        _wait_if_page_blocked(page, stage_name="打开公司详情页")
        
        # 等待搜索结果加载
        page.wait_for_load_state("networkidle")
        
        # 获取所有公司链接
        links = page.get_by_role("link").all()
        
        # 标准化目标公司名称
        normalized_target = _normalize_company_name(company_name)
        
        # 寻找匹配的链接
        target_link = None
        for link in links:
            try:
                link_text = link.inner_text().strip()
                normalized_link_text = _normalize_company_name(link_text)
                
                # 检查链接文本是否包含标准化后的目标公司名称
                if normalized_target in normalized_link_text:
                    target_link = link
                    break
            except Exception:
                continue
        
        if not target_link:
            # 如果找不到完全匹配的，尝试使用包含匹配
            for link in links:
                try:
                    link_text = link.inner_text().strip()
                    normalized_link_text = _normalize_company_name(link_text)
                    normalized_target = _normalize_company_name(company_name)
                    
                    # 检查是否有部分匹配
                    if any(part in normalized_link_text for part in normalized_target.split()):
                        target_link = link
                        break
                except Exception:
                    continue
        
        if not target_link:
            raise RuntimeError(f"未能找到公司链接: {company_name}")
        
        # 点击找到的链接
        with page.expect_popup() as popup_info:
            target_link.click()
        detail_page = popup_info.value
        detail_page.wait_for_load_state("domcontentloaded")
        return detail_page

    detail_page_result = run_step(
        open_detail_popup,
        step_name="点击公司详情链接并等待新详情页打开",
        critical=True,
        retries=2,
    )

    detail_page = detail_page_result.value
    if detail_page is None:
        raise RuntimeError(f"未能打开公司详情页: {company_name}")

    logger.info(f"[enter_company_detail_page] 已打开公司详情页: {company_name}")
    return detail_page

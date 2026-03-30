from tyc.modules.business_risk.tag_nav_extractor import extract_tag_nav_texts
from tyc.modules.business_risk.navigator import click_business_risk_tab
from tyc.modules.business_risk.date_range_filter import extract_sections_by_date
from tyc.modules.enter_company_detail_page import enter_company_detail_page
from tyc.modules.go_to_home import go_to_home_page
from loguru import logger
from playwright.sync_api import Page


def process_business_risk(
    page: Page,
    company_names: list[str]
) -> None:
    """
    处理经营风险分析的主函数
    
    Args:
        page: Playwright Page 对象
        company_names: 公司名称列表
    """
    logger.info(f"[模块] 开始处理经营风险分析，共 {len(company_names)} 家公司")
    
    # 循环：查询每个公司的经营风险分析数据
    for company_name in company_names:
        # 直接调用进入公司详情页的函数，不需要run_step包装
        detail_page = enter_company_detail_page(page, company_name)
        
        # 调用点击经营风险标签的函数
        click_business_risk_tab(detail_page)
        
        # 调用提取标签导航文本的函数，返回的标签导航文本列表
        tag_nav_texts = extract_tag_nav_texts(detail_page)
        logger.info(f"[模块] 公司 {company_name} 的经营风险标签导航文本: {tag_nav_texts}")
        
        # 调用日期范围筛选函数获取所有板块的详情
        # 这里使用默认的日期范围，实际使用时可以根据需要修改
        sections_data = extract_sections_by_date(detail_page, "2016-01-01", "2026-01-01", max_rows=20)
        logger.info(f"[模块] 公司 {company_name} 的经营风险详情数据: {sections_data}")

        # 回到首页
        go_to_home_page(page)
    logger.info("[模块] 经营风险分析处理完成")

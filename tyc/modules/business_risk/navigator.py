from loguru import logger
from playwright.sync_api import Page

from tyc.modules.run_step import run_step


def click_business_risk_tab(page: Page) -> None:
    """
    在公司详情页中点击经营风险标签
    
    Args:
        page: Playwright Page 对象
    """
    logger.info("[模块] 开始点击经营风险标签")
    
    try:
        # 使用run_step执行点击包含文本"经营风险"的按钮（非严格模式）
        run_step(
            lambda: page.get_by_text("经营风险", exact=False).first.click(),
            "点击经营风险标签",
            page_getter=lambda: page
        )
        logger.info("[模块] 经营风险标签点击成功")
    except Exception as e:
        logger.error(f"[模块] 点击经营风险标签失败: {e}")
        raise

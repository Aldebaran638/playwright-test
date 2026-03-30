from loguru import logger
from playwright.sync_api import Page

from tyc.modules.run_step import run_step


TYC_HOME_URL = "https://www.tianyancha.com/"


def go_to_home_page(page: Page) -> None:
    """
    回到天眼查首页
    
    Args:
        page: Playwright Page 对象
    """
    logger.info("[模块] 开始回到首页")
    
    try:
        # 使用run_step执行回到首页的操作
        run_step(
            lambda: page.goto(TYC_HOME_URL, wait_until="domcontentloaded"),
            "打开天眼查首页",
            page_getter=lambda: page
        )
        logger.info("[模块] 回到首页成功")
    except Exception as e:
        logger.error(f"[模块] 回到首页失败: {e}")
        raise

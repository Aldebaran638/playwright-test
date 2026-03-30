import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.business_risk.business_risk_main import process_business_risk

from tyc.modules.browser_context import launch_tyc_browser_context

from tyc.modules.login_state import wait_until_logged_in
from tyc.modules.run_step import run_step

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "company_text.json"
# 全局配置：要批量查询的公司全称列表。
TARGET_COMPANY_NAMES = [
    "小米通讯技术有限公司",
    "抖音有限公司",
    "北京三快科技有限公司",
    "深圳市维琪科技股份有限公司",
    "重庆典石信科技创新产业运营有限公司",
    "阿里巴巴（中国）有限公司",
    "深圳市腾讯计算机系统有限公司",
]
TYC_HOME_URL = "https://www.tianyancha.com/"

def get_entry_page(context: BrowserContext) -> Page:
    # 优先复用持久化上下文里已经打开的首页标签页。
    if context.pages:
        return context.pages[0]
    return context.new_page()

def run(playwright: Playwright) -> None:
    # 初始化 tyc 使用的持久化浏览器环境。
    logger.info(f"[主流程] 当前批量目标公司数: {len(TARGET_COMPANY_NAMES)}")
    context = launch_tyc_browser_context(playwright)

    try:
        page = get_entry_page(context)
        run_step(
            lambda: page.goto(TYC_HOME_URL, wait_until="domcontentloaded"),
            "打开天眼查首页",
            page_getter=lambda: page,
        )

        # 调用登录态检测模块，未登录时阻塞等待用户手动完成登录。
        logger.info("[主流程] 开始检查当前登录状态")
        wait_until_logged_in(page)

        process_business_risk(page,TARGET_COMPANY_NAMES)


    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

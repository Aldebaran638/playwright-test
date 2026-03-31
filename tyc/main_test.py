import json
import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.browser_context import launch_tyc_browser_context, save_cookies
from tyc.modules.business_risk.business_risk_main import process_business_risk
from tyc.modules.go_to_home import go_to_home_page
from tyc.modules.login_state import wait_until_logged_in
from tyc.modules.run_step import run_step


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "company_text.json"
TYC_HOME_URL = "https://www.tianyancha.com/"

EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")

TARGET_COMPANY_NAMES = [
    "阿鲁科尔沁旗罕乌拉街道理棠皮肤护理会所",
    "阿谱赛国际科技发展(北京)有限公司",
    "艾后生物科技(上海)有限公司",
    "艾琳生物制造(江苏)有限公司",
    "艾研实业(上海)有限公司",
    "艾因特丽(苏州)生物科技有限公司",
    "爱肌色(河南)生物科技有限公司",
    "爱乐士(惠州)化妆品有限公司",
    "爱生泽(上海)生物科技有限公司",
    "傲雪(广州)生物科技有限公司",
]


def save_company_results(data: list[dict]) -> None:
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_entry_page(context: BrowserContext) -> Page:
    if context.pages:
        return context.pages[0]
    return context.new_page()


def run(playwright: Playwright) -> None:
    logger.info(f"[主流程] 当前批量目标公司数: {len(TARGET_COMPANY_NAMES)}")

    context, decision_info = launch_tyc_browser_context(
        playwright,
        browser_executable_path=EDGE_EXECUTABLE_PATH,
        user_data_dir=EDGE_USER_DATA_DIR,
    )
    logger.info(f"[主流程] 浏览器环境决策: {decision_info}")

    try:
        page = get_entry_page(context)

        home_result = run_step(
            go_to_home_page,
            page,
            home_url=TYC_HOME_URL,
            step_name="打开天眼查首页",
            critical=True,
            retries=2,
        )
        if not home_result.ok:
            logger.error("[主流程] 首页打开失败，流程中止")
            return

        logger.info("[主流程] 开始检查当前登录状态")
        wait_until_logged_in(page)

        logger.info("[主流程] 登录成功，保存cookies")
        save_cookies(context)

        logger.info("[主流程] 开始批量处理经营风险")
        results = process_business_risk(page, TARGET_COMPANY_NAMES)

        logger.info("[主流程] 保存批量查询结果并退出")
        save_company_results(results)
    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

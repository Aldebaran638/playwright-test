import json
import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TYC_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.common.browser_context import launch_tyc_browser_context, save_cookies
from tyc.modules.common.go_to_home import go_to_home_page
from tyc.modules.common.login_state import wait_until_logged_in
from tyc.modules.common.run_step import StepResult, run_step
from tyc.modules.business_risk.business_risk_main import process_business_risk
from tyc.modules.company_risk.collector import collect_company_risk
from tyc.modules.company_query.batch_company_query import query_companies_sequentially
from tyc.modules.company_query.enter_company_detail_page import enter_company_detail_page


OUTPUT_FILE = TYC_ROOT / "data" / "output" / "tyc_main_results.json"
TYC_HOME_URL = "https://www.tianyancha.com/"

EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")

TARGET_COMPANY_NAMES = [
    "小米通讯技术有限公司",
    "抖音有限公司",
    "北京三快科技有限公司",
    "深圳市维琪科技股份有限公司",
    "重庆典石信科技创新产业运营有限公司",
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


def _extract_error_message(result: StepResult) -> str:
    if result.error is None:
        return "unknown error"
    return str(result.error)


def enrich_company_results_with_risk(page: Page, company_results: list[dict]) -> list[dict]:
    for result in company_results:
        result["risk_data"] = None

        if not result.get("success"):
            logger.warning(
                f"[主流程] 跳过风险采集，元信息查询失败: {result.get('company_name', '')}"
            )
            continue

        company_name = str(result.get("company_name", "")).strip()
        detail_page: Page | None = None

        try:
            logger.info(f"[主流程] 开始补充风险信息: {company_name}")

            home_result = run_step(
                go_to_home_page,
                page,
                home_url=TYC_HOME_URL,
                step_name=f"打开首页以补充风险信息: {company_name}",
                critical=False,
                retries=0,
            )
            if not home_result.ok:
                result["risk_data"] = {
                    "error": _extract_error_message(home_result),
                }
                continue

            detail_result = run_step(
                enter_company_detail_page,
                page,
                company_name,
                step_name=f"进入公司详情页以采集风险: {company_name}",
                critical=False,
                retries=0,
            )
            if not detail_result.ok or detail_result.value is None:
                result["risk_data"] = {
                    "error": _extract_error_message(detail_result),
                }
                continue

            detail_page = detail_result.value

            result["risk_data"] = collect_company_risk(detail_page)
            logger.info(f"[主流程] 风险信息补充完成: {company_name}")
        except Exception as exc:
            logger.error(f"[主流程] 风险信息补充失败: {company_name} -> {exc}")
            result["risk_data"] = {
                "should_collect": False,
                "selected_risk_type": None,
                "selected_risk_count": 0,
                "available_risks": [],
                "risk_page_url": "",
                "risk_details": None,
                "error": str(exc),
            }
        finally:
            if detail_page is not None and detail_page is not page:
                try:
                    if not detail_page.is_closed():
                        detail_page.close()
                except Exception:
                    logger.warning(f"[主流程] 关闭风险采集详情页时出现异常: {company_name}")

    return company_results


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

        logger.info("[主流程] 调用批量公司查询模块")
        company_results = query_companies_sequentially(
            page,
            TARGET_COMPANY_NAMES,
            home_url=TYC_HOME_URL,
            stop_on_error=False,
            return_to_home_each_time=True,
        )

        logger.info("[主流程] 开始在 main 中补充每家公司的风险信息")
        company_results = enrich_company_results_with_risk(page, company_results)

        logger.info("[主流程] 保存批量查询结果并退出")
        save_company_results(company_results)
    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

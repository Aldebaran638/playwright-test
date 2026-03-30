import json
import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.batch_company_query import query_companies_sequentially
from tyc.modules.browser_context import launch_tyc_browser_context
from tyc.modules.company_risk.collector import collect_company_risk
from tyc.modules.enter_company_detail_page import enter_company_detail_page
from tyc.modules.login_state import wait_until_logged_in
from tyc.modules.run_step import run_step
from tyc.modules.business_risk.analyzer import analyze_company_business_risk


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "company_text.json"
# 全局配置：要批量查询的公司全称列表。
TARGET_COMPANY_NAMES = [
    "小米通讯技术有限公司",
    "抖音有限公司",
    "北京三快科技有限公司",
    "深圳市维琪科技股份有限公司",
    "重庆典石信科技创新产业运营有限公司",
]
TYC_HOME_URL = "https://www.tianyancha.com/"


def save_company_results(data: list[dict]) -> None:
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_entry_page(context: BrowserContext) -> Page:
    # 优先复用持久化上下文里已经打开的首页标签页。
    if context.pages:
        return context.pages[0]
    return context.new_page()


def enrich_company_results_with_risk(page: Page, company_results: list[dict]) -> list[dict]:
    # 在批量元信息查询完成后，再逐个补充每家公司的风险信息。
    for result in company_results:
        result["risk_data"] = None

        # 只有元信息查询成功的公司，才继续补充风险详情。
        if not result.get("success"):
            logger.warning(
                f"[主流程] 跳过风险采集，元信息查询失败: {result.get('company_name', '')}"
            )
            continue

        company_name = str(result.get("company_name", "")).strip()
        detail_page: Page | None = None

        try:
            logger.info(f"[主流程] 开始补充风险信息: {company_name}")

            # 每轮都回到首页后再进详情页，降低页面状态污染的影响。
            run_step(
                lambda: page.goto(TYC_HOME_URL, wait_until="domcontentloaded"),
                f"打开首页以补充风险信息: {company_name}",
                page_getter=lambda: page,
            )

            # 重新进入当前公司的详情页，给风险采集模块提供正确的详情页对象。
            detail_page = enter_company_detail_page(page, company_name)
            run_step(
                lambda: detail_page.wait_for_load_state("domcontentloaded"),
                f"等待详情页加载完成以采集风险信息: {company_name}",
                page_getter=lambda: detail_page,
            )

            # 调用风险采集模块，按固定顺序选择第一个非零风险入口并提取内容。
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
            # 每轮结束后关闭临时打开的公司详情页，避免标签页越积越多。
            if detail_page is not None and detail_page is not page:
                try:
                    if not detail_page.is_closed():
                        detail_page.close()
                except Exception:
                    logger.warning(f"[主流程] 关闭风险采集详情页时出现异常: {company_name}")

    return company_results


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

        # # 调用批量查询模块，按顺序逐个查询目标公司。
        # logger.info("[主流程] 调用批量公司查询模块")
        # company_results = query_companies_sequentially(
        #     page,
        #     TARGET_COMPANY_NAMES,
        #     home_url=TYC_HOME_URL,
        #     stop_on_error=False,
        #     return_to_home_each_time=True,
        # )

        # # 在批量元信息查询结果的基础上，再逐个补充风险信息。
        # logger.info("[主流程] 开始在 main 中补充每家公司的风险信息")
        # company_results = enrich_company_results_with_risk(page, company_results)

        # 分析深圳市维琪科技股份有限公司的经营风险VIP需求
        logger.info("[主流程] 开始分析深圳市维琪科技股份有限公司的经营风险")
        company_name = "深圳市维琪科技股份有限公司"
        business_risk_result = analyze_company_business_risk(page, company_name, TYC_HOME_URL)
        
        # 保存分析结果
        company_results = [business_risk_result]

        # 保存整批查询结果，然后结束本次运行。
        logger.info("[主流程] 保存批量查询结果并退出")
        save_company_results(company_results)
    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

from dataclasses import asdict
from typing import Any

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.company_risk.models import DEFAULT_MAX_CAPTURE_COUNT
from tyc.modules.company_risk.navigator import open_first_available_risk_page
from tyc.modules.company_risk.page_extractor import extract_company_risk_page


def collect_company_risk(
    page: Page,
    *,
    max_capture_count: int = DEFAULT_MAX_CAPTURE_COUNT,
) -> dict[str, Any]:
    # 串联风险入口扫描和风险页提取，统一返回当前公司的风险采集结果。
    logger.info("[模块] 开始收集公司风险信息")
    navigation_result, risk_page = open_first_available_risk_page(page)
    result: dict[str, Any] = {
        "should_collect": navigation_result.should_collect,
        "selected_risk_type": navigation_result.selected_risk_type,
        "selected_risk_count": navigation_result.selected_risk_count,
        "available_risks": [asdict(item) for item in navigation_result.available_risks],
        "risk_page_url": "",
        "risk_details": None,
    }

    if not navigation_result.should_collect or risk_page is None:
        logger.info("[模块] 本次没有可进入的风险详情页，直接返回概览结果")
        return result

    try:
        result["risk_page_url"] = risk_page.url
        result["risk_details"] = extract_company_risk_page(
            risk_page,
            preferred_risk_type=navigation_result.selected_risk_type,
            max_capture_count=max_capture_count,
            source=risk_page.url,
        )
        return result
    finally:
        # 风险详情页是临时弹出的新页，采集结束后及时关闭，避免影响后续流程。
        if not risk_page.is_closed():
            risk_page.close()

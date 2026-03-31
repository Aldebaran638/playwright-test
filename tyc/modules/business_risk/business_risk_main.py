import json
from pathlib import Path
from typing import Any

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.business_risk.date_range_filter import extract_sections_by_date
from tyc.modules.business_risk.navigator import click_business_risk_tab
from tyc.modules.business_risk.tag_nav_extractor import extract_tag_nav_texts
from tyc.modules.enter_company_detail_page import enter_company_detail_page
from tyc.modules.go_to_home import go_to_home_page
from tyc.modules.run_step import StepResult, run_step


DEFAULT_DATE_START = "2016-01-01"
DEFAULT_DATE_END = "2026-01-01"
DEFAULT_MAX_ROWS = 20

# 定义输出文件路径
OUTPUT_FILE = Path(__file__).resolve().parents[2] / "company_text.json"


def _extract_error_message(result: StepResult[Any]) -> str:
    if result.error is None:
        return "unknown error"
    return str(result.error)


def _save_results(results: list[dict[str, Any]]) -> None:
    """保存结果到文件"""
    try:
        OUTPUT_FILE.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"[business_risk.main] 已保存结果到: {OUTPUT_FILE}")
    except Exception as exc:
        logger.error(f"[business_risk.main] 保存结果失败: {exc}")


def process_business_risk(
    page: Page,
    company_names: list[str],
    *,
    date_start: str = DEFAULT_DATE_START,
    date_end: str = DEFAULT_DATE_END,
    max_rows: int = DEFAULT_MAX_ROWS,
    return_to_home_each_time: bool = True,
) -> list[dict[str, Any]]:
    logger.info(f"[business_risk.main] 开始处理经营风险分析，公司数: {len(company_names)}")
    results: list[dict[str, Any]] = []

    # 逐个处理公司，单家公司失败时记录结果后继续处理下一家。
    for company_name in company_names:
        logger.info(f"[business_risk.main] 开始处理公司: {company_name}")
        detail_page: Page | None = None
        company_result: dict[str, Any] = {
            "company_name": company_name,
            "success": False,
            "tag_nav_texts": [],
            "sections_data": [],
            "error": "",
        }

        try:
            if return_to_home_each_time:
                home_result = run_step(
                    go_to_home_page,
                    page,
                    step_name=f"回到首页准备采集经营风险: {company_name}",
                    critical=False,
                    retries=0,
                )
                if not home_result.ok:
                    company_result["error"] = _extract_error_message(home_result)
                    results.append(company_result)
                    logger.warning(f"[business_risk.main] 首页恢复失败，已跳过公司: {company_name}")
                    continue

            detail_result = run_step(
                enter_company_detail_page,
                page,
                company_name,
                step_name=f"进入公司详情页: {company_name}",
                critical=False,
                retries=0,
            )
            if not detail_result.ok or detail_result.value is None:
                company_result["error"] = _extract_error_message(detail_result)
                results.append(company_result)
                logger.warning(f"[business_risk.main] 公司详情页打开失败，已跳过公司: {company_name}")
                continue

            detail_page = detail_result.value

            tab_result = run_step(
                click_business_risk_tab,
                detail_page,
                step_name=f"点击经营风险标签: {company_name}",
                critical=False,
                retries=0,
            )
            if not tab_result.ok:
                company_result["error"] = _extract_error_message(tab_result)
                results.append(company_result)
                logger.warning(f"[business_risk.main] 经营风险标签打开失败，已跳过公司: {company_name}")
                continue

            tag_result = run_step(
                extract_tag_nav_texts,
                detail_page,
                step_name=f"提取经营风险标签导航: {company_name}",
                critical=False,
                retries=0,
            )
            if not tag_result.ok or tag_result.value is None:
                company_result["error"] = _extract_error_message(tag_result)
                results.append(company_result)
                logger.warning(f"[business_risk.main] 标签导航提取失败，已跳过公司: {company_name}")
                continue

            sections_result = run_step(
                extract_sections_by_date,
                detail_page,
                date_start,
                date_end,
                max_rows=max_rows,
                step_name=f"提取经营风险板块详情: {company_name}",
                critical=False,
                retries=0,
            )
            if not sections_result.ok or sections_result.value is None:
                company_result["error"] = _extract_error_message(sections_result)
                results.append(company_result)
                logger.warning(f"[business_risk.main] 板块详情提取失败，已跳过公司: {company_name}")
                continue

            company_result["success"] = True
            company_result["tag_nav_texts"] = tag_result.value
            company_result["sections_data"] = sections_result.value
            results.append(company_result)
            logger.info(f"[business_risk.main] 公司经营风险提取完成: {company_name}")
        finally:
            # 每轮结束后关闭详情页，避免弹出的标签页越积越多。
            if detail_page is not None and detail_page is not page:
                try:
                    if not detail_page.is_closed():
                        detail_page.close()
                except Exception:
                    logger.warning(f"[business_risk.main] 关闭详情页时出现异常: {company_name}")
        
        # 每处理完一家公司就保存一次结果
        _save_results(results)

    logger.info(f"[business_risk.main] 经营风险分析处理完成，结果数: {len(results)}")
    return results

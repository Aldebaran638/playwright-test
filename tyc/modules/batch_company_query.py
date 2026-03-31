from typing import Any

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.company_metadata import extract_company_metadata
from tyc.modules.enter_company_detail_page import enter_company_detail_page
from tyc.modules.go_to_home import go_to_home_page
from tyc.modules.run_step import StepResult, run_step


TYC_HOME_URL = "https://www.tianyancha.com/"


def _build_company_result(
    company_name: str,
    *,
    success: bool,
    data: dict[str, Any] | None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "company_name": company_name,
        "success": success,
        "data": data,
        "error": error,
    }


def _extract_error_message(result: StepResult[Any]) -> str:
    if result.error is None:
        return "unknown error"
    return str(result.error)


def query_companies_sequentially(
    page: Page,
    company_names: list[str],
    *,
    home_url: str = TYC_HOME_URL,
    stop_on_error: bool = False,
    return_to_home_each_time: bool = True,
) -> list[dict[str, Any]]:
    logger.info(f"[batch_company_query] 开始批量查询公司，总数: {len(company_names)}")
    results: list[dict[str, Any]] = []

    for company_name in company_names:
        logger.info(f"[batch_company_query] 开始处理公司: {company_name}")
        detail_page: Page | None = None
        try:
            if return_to_home_each_time:
                home_result = run_step(
                    go_to_home_page,
                    page,
                    home_url=home_url,
                    step_name=f"回到首页准备查询公司: {company_name}",
                    critical=False,
                    retries=0,
                )
                if not home_result.ok:
                    results.append(
                        _build_company_result(
                            company_name,
                            success=False,
                            data=None,
                            error=_extract_error_message(home_result),
                        )
                    )
                    logger.warning(f"[batch_company_query] 公司查询失败，已跳过: {company_name}")
                    if stop_on_error:
                        break
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
                results.append(
                    _build_company_result(
                        company_name,
                        success=False,
                        data=None,
                        error=_extract_error_message(detail_result),
                    )
                )
                logger.warning(f"[batch_company_query] 公司详情页打开失败，已跳过: {company_name}")
                if stop_on_error:
                    break
                continue

            detail_page = detail_result.value
            metadata_result = run_step(
                extract_company_metadata,
                detail_page,
                source=detail_page.url,
                step_name=f"提取公司元信息: {company_name}",
                critical=False,
                retries=0,
            )
            if not metadata_result.ok or metadata_result.value is None:
                results.append(
                    _build_company_result(
                        company_name,
                        success=False,
                        data=None,
                        error=_extract_error_message(metadata_result),
                    )
                )
                logger.warning(f"[batch_company_query] 公司元信息提取失败，已跳过: {company_name}")
                if stop_on_error:
                    break
                continue

            results.append(
                _build_company_result(
                    company_name,
                    success=True,
                    data=metadata_result.value,
                )
            )
            logger.info(f"[batch_company_query] 公司查询完成: {company_name}")
        finally:
            # 每轮结束后关闭详情页，避免标签页累计影响后续查询。
            if detail_page is not None and detail_page is not page:
                try:
                    if not detail_page.is_closed():
                        detail_page.close()
                except Exception:
                    logger.warning(f"[batch_company_query] 关闭详情页时出现异常: {company_name}")

    logger.info(f"[batch_company_query] 批量查询完成，结果数: {len(results)}")
    return results

from typing import Any

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.company_metadata import extract_company_metadata
from tyc.modules.enter_company_detail_page import enter_company_detail_page
from tyc.modules.run_step import run_step


TYC_HOME_URL = "https://www.tianyancha.com/"


def query_companies_sequentially(
    page: Page,
    company_names: list[str],
    *,
    home_url: str = TYC_HOME_URL,
    stop_on_error: bool = False,
    return_to_home_each_time: bool = True,
) -> list[dict[str, Any]]:
    # 按顺序逐个查询公司，并把每家公司的执行结果统一收集起来。
    results: list[dict[str, Any]] = []

    for company_name in company_names:
        logger.info(f"[模块] 开始批量查询公司: {company_name}")
        detail_page: Page | None = None

        try:
            # 每轮回到首页可以降低页面状态污染，优先保证稳定性。
            if return_to_home_each_time:
                run_step(
                    lambda: page.goto(home_url, wait_until="domcontentloaded"),
                    f"打开首页以查询公司: {company_name}",
                    page_getter=lambda: page,
                )

            detail_page = enter_company_detail_page(page, company_name)
            run_step(
                lambda: detail_page.wait_for_load_state("domcontentloaded"),
                f"等待详情页加载完成: {company_name}",
                page_getter=lambda: detail_page,
            )
            # 从详情页提取公司数据
            company_data = extract_company_metadata(detail_page, source=detail_page.url)
            results.append(
                {
                    "company_name": company_name,
                    "success": True,
                    "data": company_data,
                    "error": "",
                }
            )
            logger.info(f"[模块] 公司查询完成: {company_name}")
        except Exception as exc:
            logger.error(f"[模块] 公司查询失败: {company_name} -> {exc}")
            results.append(
                {
                    "company_name": company_name,
                    "success": False,
                    "data": None,
                    "error": str(exc),
                }
            )

            if stop_on_error:
                break
        finally:
            # 新开的详情页在每轮结束后关闭，避免标签页越积越多。
            if detail_page is not None and detail_page is not page:
                try:
                    if not detail_page.is_closed():
                        detail_page.close()
                except Exception:
                    logger.warning(f"[模块] 关闭详情页时出现异常: {company_name}")

    return results

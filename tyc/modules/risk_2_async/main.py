from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from playwright.async_api import BrowserContext, Page, async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2_async.browser_context_async import (
    launch_tyc_browser_context_async,
    save_cookies_async,
)
from tyc.modules.risk_2_async.extract_async import extract_risk_data_async
from tyc.modules.risk_2_async.login_state_async import wait_until_logged_in_async
from tyc.modules.risk_2_async.navigate_async import navigate_to_risk_page_async
from tyc.modules.risk_2_async.paging_async import (
    has_next_page_async,
    should_continue_paging,
    turn_page_async,
)
from tyc.modules.risk_2_async.run_step_async import run_step_async


RISK_SEARCH_URL = "https://www.tianyancha.com/risk"
TYC_HOME_URL = "https://www.tianyancha.com/"
OUTPUT_FILE = Path(__file__).resolve().parent / "risk_2_async_results.json"

DATE_START = "2020-01-01"
DATE_END = "2026-12-31"
MAX_QUERY_COUNT = 100
MAX_PAGE_TURNS = 20
DEVELOPER_WORKER_COUNT = 3

EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")


def load_companies_from_file() -> List[str]:
    name_list_path = Path(__file__).resolve().parents[1] / "name_list_test.txt"
    if not name_list_path.exists():
        logger.error(f"[risk_2_async.main] 公司列表文件不存在: {name_list_path}")
        return []

    try:
        with open(name_list_path, "r", encoding="utf-8") as file_obj:
            companies = [line.strip() for line in file_obj if line.strip()]
        logger.info(f"[risk_2_async.main] 从文件中读取了 {len(companies)} 个公司")
        return companies
    except Exception as exc:
        logger.error(f"[risk_2_async.main] 读取公司列表文件失败: {exc}")
        return []


def validate_dates() -> bool:
    try:
        start_date = datetime.strptime(DATE_START, "%Y-%m-%d")
        end_date = datetime.strptime(DATE_END, "%Y-%m-%d")
        if end_date <= start_date:
            logger.error(f"[risk_2_async.main] 结束日期 {DATE_END} 必须晚于起始日期 {DATE_START}")
            return False
        logger.info(f"[risk_2_async.main] 日期验证通过：{DATE_START} 至 {DATE_END}")
        return True
    except ValueError as exc:
        logger.error(f"[risk_2_async.main] 日期格式错误：{exc}")
        return False


def split_companies_evenly(companies: List[str], worker_count: int) -> List[List[str]]:
    if not companies:
        return []

    actual_worker_count = max(1, min(worker_count, len(companies)))
    base_size, remainder = divmod(len(companies), actual_worker_count)
    chunks: List[List[str]] = []

    start = 0
    for index in range(actual_worker_count):
        chunk_size = base_size + (1 if index < remainder else 0)
        end = start + chunk_size
        chunk = companies[start:end]
        if chunk:
            chunks.append(chunk)
        start = end

    return chunks


async def reset_to_search_page_async(page: Page) -> None:
    logger.info("[risk_2_async.main] 重置到查风险搜索页")
    await run_step_async(
        page.goto,
        RISK_SEARCH_URL,
        step_name="跳转到查风险搜索页",
        critical=True,
        retries=1,
    )
    await run_step_async(
        page.get_by_role("textbox").first.wait_for,
        step_name="等待搜索框加载",
        critical=True,
        retries=2,
    )


def _save_results(
    results: List[Dict[str, Any]],
    failed_companies: List[str],
    worker_count: int,
) -> None:
    try:
        output_data = {
            "analysis_params": {
                "date_start": DATE_START,
                "date_end": DATE_END,
                "worker_count": worker_count,
            },
            "successful_results": results,
            "failed_companies": failed_companies,
        }
        OUTPUT_FILE.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"[risk_2_async.main] 已保存结果到: {OUTPUT_FILE}")
    except Exception as exc:
        logger.error(f"[risk_2_async.main] 保存结果失败: {exc}")


def _build_company_result(company: str, risk_records: Any) -> Dict[str, Any]:
    if isinstance(risk_records, list):
        normalized_records = risk_records
    else:
        normalized_records = []
    return {
        "company_name": company,
        "success": True,
        "risk_records": normalized_records,
    }


def _abort_worker(
    worker_id: int,
    companies: List[str],
    next_index: int,
    failed_companies: List[str],
    reason: str,
) -> None:
    remaining = companies[next_index:]
    if remaining:
        logger.error(f"[risk_2_async.worker{worker_id}] {reason}，剩余 {len(remaining)} 个公司标记为失败")
        failed_companies.extend(remaining)


async def process_company_batch_async(
    page: Page,
    companies: List[str],
    worker_id: int,
) -> tuple[List[Dict[str, Any]], List[str]]:
    results: List[Dict[str, Any]] = []
    failed_companies: List[str] = []

    logger.info(f"[risk_2_async.worker{worker_id}] 开始处理分片，公司数: {len(companies)}")

    for index, company in enumerate(companies):
        if index > 0 and index % 10 == 0:
            logger.info(f"[risk_2_async.worker{worker_id}] 已处理10个公司，开始延迟5秒")
            await asyncio.sleep(5)

        logger.info(
            f"[risk_2_async.worker{worker_id}] 开始处理公司: {company} "
            f"(第{index + 1}/{len(companies)}个)"
        )

        nav = await run_step_async(
            navigate_to_risk_page_async,
            page,
            company,
            step_name=f"worker{worker_id}-导航-{company}",
            critical=False,
            retries=1,
        )
        if not nav.ok:
            failed_companies.append(company)
            try:
                await reset_to_search_page_async(page)
            except Exception:
                _abort_worker(worker_id, companies, index + 1, failed_companies, "导航失败后重置搜索页失败")
                break
            continue

        if not nav.value:
            try:
                await reset_to_search_page_async(page)
            except Exception:
                _abort_worker(worker_id, companies, index + 1, failed_companies, "未找到风险信息后重置搜索页失败")
                break
            continue

        all_risk_records: List[Dict[str, Any]] = []
        page_turn_count = 0
        extract_success = True

        while page_turn_count <= MAX_PAGE_TURNS and len(all_risk_records) < MAX_QUERY_COUNT:
            ext = await run_step_async(
                extract_risk_data_async,
                page,
                company,
                DATE_START,
                DATE_END,
                step_name=f"worker{worker_id}-提取-{company}-第{page_turn_count + 1}页",
                critical=False,
                retries=0,
            )
            if not ext.ok:
                extract_success = False
                break

            if isinstance(ext.value, list):
                all_risk_records.extend(ext.value)

            if len(all_risk_records) >= MAX_QUERY_COUNT:
                break
            if not should_continue_paging(all_risk_records, DATE_START, DATE_END):
                break
            if not await has_next_page_async(page):
                break
            if not await turn_page_async(page):
                extract_success = False
                break
            page_turn_count += 1

        if not extract_success:
            failed_companies.append(company)
            try:
                await reset_to_search_page_async(page)
            except Exception:
                _abort_worker(worker_id, companies, index + 1, failed_companies, "提取失败后重置搜索页失败")
                break
            continue

        results.append(_build_company_result(company, all_risk_records))

        try:
            await reset_to_search_page_async(page)
        except Exception:
            _abort_worker(worker_id, companies, index + 1, failed_companies, "正常完成后重置搜索页失败")
            break

    logger.info(f"[risk_2_async.worker{worker_id}] 分片处理完成，成功: {len(results)}, 失败: {len(failed_companies)}")
    return results, failed_companies


async def process_risk_2_async(
    companies: List[str],
    *,
    worker_count: int,
    browser_executable_path: Path | None = None,
    user_data_dir: Path | None = None,
    headless: bool = False,
) -> tuple[List[Dict[str, Any]], List[str]]:
    logger.info(f"[risk_2_async.main] 开始处理风险2分析，公司数: {len(companies)}")

    if worker_count < 1:
        raise ValueError(f"worker_count 必须大于等于 1，当前值: {worker_count}")

    if not validate_dates():
        return [], companies

    if browser_executable_path is None:
        browser_executable_path = EDGE_EXECUTABLE_PATH
    if user_data_dir is None:
        user_data_dir = EDGE_USER_DATA_DIR

    results: List[Dict[str, Any]] = []
    failed_companies: List[str] = []

    async with async_playwright() as playwright:
        context: BrowserContext | None = None

        try:
            context_result = await run_step_async(
                launch_tyc_browser_context_async,
                playwright,
                browser_executable_path,
                user_data_dir,
                headless,
                step_name="启动异步浏览器上下文",
                critical=True,
                retries=0,
            )
            if not context_result.ok or context_result.value is None:
                return results, companies

            context, decision_info = context_result.value
            logger.info(f"[risk_2_async.main] 浏览器环境决策: {decision_info}")

            page0 = context.pages[0] if context.pages else await context.new_page()
            await run_step_async(
                page0.goto,
                TYC_HOME_URL,
                wait_until="domcontentloaded",
                step_name="打开天眼查首页",
                critical=True,
                retries=2,
            )
            await wait_until_logged_in_async(page0)
            await save_cookies_async(context)

            company_chunks = split_companies_evenly(companies, worker_count)
            worker_plans: List[tuple[int, Page, List[str]]] = []

            for worker_id, company_chunk in enumerate(company_chunks, start=1):
                worker_page = await context.new_page()
                await reset_to_search_page_async(worker_page)
                worker_plans.append((worker_id, worker_page, company_chunk))
                logger.info(f"[risk_2_async.main] worker{worker_id} 初始化完成，分配公司数: {len(company_chunk)}")

            worker_tasks = [
                process_company_batch_async(worker_page, company_chunk, worker_id)
                for worker_id, worker_page, company_chunk in worker_plans
            ]
            worker_outputs = await asyncio.gather(*worker_tasks, return_exceptions=True)

            for index, output in enumerate(worker_outputs):
                worker_id, _, company_chunk = worker_plans[index]
                if isinstance(output, Exception):
                    logger.error(f"[risk_2_async.main] worker{worker_id} 执行异常: {output}")
                    failed_companies.extend(company_chunk)
                    continue
                worker_results, worker_failed = output
                results.extend(worker_results)
                failed_companies.extend(worker_failed)

            logger.info(f"[risk_2_async.main] 所有公司处理完成，成功: {len(results)}, 失败: {len(failed_companies)}")
        except Exception as exc:
            logger.error(f"[risk_2_async.main] 处理过程中发生异常: {exc}")
            processed_companies = {item.get('company_name') for item in results if isinstance(item, dict)}
            for company in companies:
                if company not in processed_companies and company not in failed_companies:
                    failed_companies.append(company)
        finally:
            if context is not None:
                await run_step_async(
                    context.close,
                    step_name="关闭异步浏览器上下文",
                    critical=False,
                    retries=0,
                )

    _save_results(results, failed_companies, worker_count)
    return results, failed_companies


async def amain() -> None:
    companies = load_companies_from_file()
    if not companies:
        logger.error("[risk_2_async.main] 未加载到公司列表，中止测试")
        return

    results, failed = await process_risk_2_async(
        companies=companies,
        worker_count=DEVELOPER_WORKER_COUNT,
        browser_executable_path=EDGE_EXECUTABLE_PATH,
        user_data_dir=EDGE_USER_DATA_DIR,
        headless=False,
    )
    logger.info(f"[risk_2_async.main] 测试完成，成功: {len(results)}, 失败: {len(failed)}")


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
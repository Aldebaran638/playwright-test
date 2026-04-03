from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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


@dataclass(slots=True)
class Risk2AsyncConfig:
    search_url: str
    home_url: str
    date_start: str
    date_end: str
    max_query_count: int
    max_page_turns: int
    worker_count: int
    browser_executable_path: Path | None
    user_data_dir: Path | None
    headless: bool
    pause_every_n_companies: int
    pause_seconds: float


def load_companies_from_file(input_file: str | Path) -> list[str]:
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"[risk_2_async.main] 公司列表文件不存在: {input_path}")
        return []

    try:
        with open(input_path, "r", encoding="utf-8") as file_obj:
            companies = [line.strip() for line in file_obj if line.strip()]
        logger.info(f"[risk_2_async.main] 从文件中读取了 {len(companies)} 个公司")
        return companies
    except Exception as exc:
        logger.error(f"[risk_2_async.main] 读取公司列表文件失败: {exc}")
        return []


def validate_dates(date_start: str, date_end: str) -> bool:
    try:
        start_date = datetime.strptime(date_start, "%Y-%m-%d")
        end_date = datetime.strptime(date_end, "%Y-%m-%d")
        if end_date <= start_date:
            logger.error(f"[risk_2_async.main] 结束日期 {date_end} 必须晚于起始日期 {date_start}")
            return False
        logger.info(f"[risk_2_async.main] 日期验证通过：{date_start} 至 {date_end}")
        return True
    except ValueError as exc:
        logger.error(f"[risk_2_async.main] 日期格式错误：{exc}")
        return False


def split_companies_evenly(companies: list[str], worker_count: int) -> list[list[str]]:
    if not companies:
        return []

    actual_worker_count = max(1, min(worker_count, len(companies)))
    base_size, remainder = divmod(len(companies), actual_worker_count)
    chunks: list[list[str]] = []

    start = 0
    for index in range(actual_worker_count):
        chunk_size = base_size + (1 if index < remainder else 0)
        end = start + chunk_size
        chunk = companies[start:end]
        if chunk:
            chunks.append(chunk)
        start = end

    return chunks


async def reset_to_search_page_async(page: Page, *, search_url: str) -> None:
    logger.info("[risk_2_async.main] 重置到查风险搜索页")
    await run_step_async(
        page.goto,
        search_url,
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


def save_risk_results(
    output_file: str | Path,
    results: list[dict[str, Any]],
    failed_companies: list[str],
    *,
    date_start: str,
    date_end: str,
    worker_count: int,
) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "analysis_params": {
            "date_start": date_start,
            "date_end": date_end,
            "worker_count": worker_count,
        },
        "successful_results": results,
        "failed_companies": failed_companies,
    }
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"[risk_2_async.main] 已保存结果到: {output_path}")


def _build_company_result(company: str, risk_records: Any) -> dict[str, Any]:
    normalized_records = risk_records if isinstance(risk_records, list) else []
    return {
        "company_name": company,
        "success": True,
        "risk_records": normalized_records,
    }


def _abort_worker(
    worker_id: int,
    companies: list[str],
    next_index: int,
    failed_companies: list[str],
    reason: str,
) -> None:
    remaining = companies[next_index:]
    if remaining:
        logger.error(f"[risk_2_async.worker{worker_id}] {reason}，剩余 {len(remaining)} 个公司标记为失败")
        failed_companies.extend(remaining)


async def process_company_batch_async(
    page: Page,
    companies: list[str],
    worker_id: int,
    *,
    config: Risk2AsyncConfig,
) -> tuple[list[dict[str, Any]], list[str]]:
    results: list[dict[str, Any]] = []
    failed_companies: list[str] = []

    logger.info(f"[risk_2_async.worker{worker_id}] 开始处理分片，公司数: {len(companies)}")

    for index, company in enumerate(companies):
        if config.pause_every_n_companies > 0 and index > 0 and index % config.pause_every_n_companies == 0:
            logger.info(
                f"[risk_2_async.worker{worker_id}] 已处理 {config.pause_every_n_companies} 个公司，开始暂停 {config.pause_seconds} 秒"
            )
            await asyncio.sleep(config.pause_seconds)

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
                await reset_to_search_page_async(page, search_url=config.search_url)
            except Exception:
                _abort_worker(worker_id, companies, index + 1, failed_companies, "导航失败后重置搜索页失败")
                break
            continue

        if not nav.value:
            try:
                await reset_to_search_page_async(page, search_url=config.search_url)
            except Exception:
                _abort_worker(worker_id, companies, index + 1, failed_companies, "未找到风险信息后重置搜索页失败")
                break
            continue

        all_risk_records: list[dict[str, Any]] = []
        page_turn_count = 0
        extract_success = True

        while page_turn_count <= config.max_page_turns and len(all_risk_records) < config.max_query_count:
            ext = await run_step_async(
                extract_risk_data_async,
                page,
                company,
                config.date_start,
                config.date_end,
                step_name=f"worker{worker_id}-提取-{company}-第{page_turn_count + 1}页",
                critical=False,
                retries=0,
            )
            if not ext.ok:
                extract_success = False
                break

            if isinstance(ext.value, list):
                all_risk_records.extend(ext.value)

            if len(all_risk_records) >= config.max_query_count:
                break
            if not should_continue_paging(all_risk_records, config.date_start, config.date_end):
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
                await reset_to_search_page_async(page, search_url=config.search_url)
            except Exception:
                _abort_worker(worker_id, companies, index + 1, failed_companies, "提取失败后重置搜索页失败")
                break
            continue

        results.append(_build_company_result(company, all_risk_records))

        try:
            await reset_to_search_page_async(page, search_url=config.search_url)
        except Exception:
            _abort_worker(worker_id, companies, index + 1, failed_companies, "正常完成后重置搜索页失败")
            break

    logger.info(f"[risk_2_async.worker{worker_id}] 分片处理完成，成功: {len(results)}, 失败: {len(failed_companies)}")
    return results, failed_companies


async def process_risk_2_async(
    companies: list[str],
    *,
    config: Risk2AsyncConfig,
) -> tuple[list[dict[str, Any]], list[str]]:
    logger.info(f"[risk_2_async.main] 开始处理风险2分析，公司数: {len(companies)}")

    if config.worker_count < 1:
        raise ValueError(f"worker_count 必须大于等于 1，当前值: {config.worker_count}")

    if not validate_dates(config.date_start, config.date_end):
        return [], companies

    results: list[dict[str, Any]] = []
    failed_companies: list[str] = []

    async with async_playwright() as playwright:
        context: BrowserContext | None = None

        try:
            context_result = await run_step_async(
                launch_tyc_browser_context_async,
                playwright,
                config.browser_executable_path,
                config.user_data_dir,
                config.headless,
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
                config.home_url,
                wait_until="domcontentloaded",
                step_name="打开天眼查首页",
                critical=True,
                retries=2,
            )
            await wait_until_logged_in_async(page0)
            await save_cookies_async(context)

            company_chunks = split_companies_evenly(companies, config.worker_count)
            worker_plans: list[tuple[int, Page, list[str]]] = []

            for worker_id, company_chunk in enumerate(company_chunks, start=1):
                worker_page = await context.new_page()
                await reset_to_search_page_async(worker_page, search_url=config.search_url)
                worker_plans.append((worker_id, worker_page, company_chunk))
                logger.info(f"[risk_2_async.main] worker{worker_id} 初始化完成，分配公司数: {len(company_chunk)}")

            worker_tasks = [
                process_company_batch_async(worker_page, company_chunk, worker_id, config=config)
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
            processed_companies = {item.get("company_name") for item in results if isinstance(item, dict)}
            for company in companies:
                if company not in processed_companies and company not in failed_companies:
                    failed_companies.append(company)
        finally:
            if context is not None:
                close_result = await run_step_async(
                    context.close,
                    step_name="关闭异步浏览器上下文",
                    critical=False,
                    retries=0,
                )
                if close_result.error is not None and "has been closed" not in str(close_result.error):
                    logger.warning(f"[risk_2_async.main] 关闭上下文时出现异常: {close_result.error}")

    return results, failed_companies
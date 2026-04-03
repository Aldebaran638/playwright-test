from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger
from playwright.async_api import Page

from tyc.modules.risk_2_async.extract_async import _extract_date_from_string
from tyc.modules.risk_2_async.run_step_async import run_step_async


def has_valid_date_in_range(record: Dict[str, Any], start_date: str, end_date: str) -> bool:
    fields = record.get("fields", {})
    for key, value in fields.items():
        if not any(keyword in key for keyword in ["日期", "时间", "刊登", "发布", "发生"]):
            continue
        values = value if isinstance(value, list) else [value]
        for one_value in values:
            date_str = _extract_date_from_string(str(one_value))
            if not date_str:
                continue
            try:
                record_date = datetime.strptime(date_str, "%Y-%m-%d")
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                if start <= record_date <= end:
                    return True
            except ValueError:
                continue
    return False


def should_continue_paging(records: List[Dict[str, Any]], start_date: str, end_date: str) -> bool:
    if not records:
        return True
    return has_valid_date_in_range(records[-1], start_date, end_date)


async def has_next_page_async(page: Page) -> bool:
    try:
        next_button = page.locator(".tic.tic-laydate-next-m")
        return await next_button.count() > 0
    except Exception:
        return False


async def turn_page_async(page: Page) -> bool:
    try:
        next_button = page.locator(".tic.tic-laydate-next-m")
        await next_button.wait_for(state="visible", timeout=5000)

        turn_result = await run_step_async(
            next_button.click,
            step_name="点击下一页",
            critical=True,
            retries=1,
        )
        if not turn_result.ok:
            return False

        wait_result = await run_step_async(
            page.wait_for_load_state,
            "networkidle",
            step_name="等待新页面加载",
            critical=True,
            retries=2,
        )
        return wait_result.ok
    except Exception as exc:
        logger.warning(f"[risk_2_async.paging] 翻页失败: {exc}")
        return False
"""
翻页模块 - 处理风险查询的翻页逻辑
"""

from typing import Dict, Any, List
from datetime import datetime
from loguru import logger
from playwright.sync_api import Page

from tyc.modules.risk_2.extract import _extract_date_from_string
from tyc.modules.run_step import run_step


def has_valid_date_in_range(record: Dict[str, Any], start_date: str, end_date: str) -> bool:
    """
    检查记录是否有符合日期范围的日期字段

    Args:
        record: 风险记录
        start_date: 起始日期字符串
        end_date: 结束日期字符串

    Returns:
        bool: True表示有符合日期范围的日期字段，False表示没有
    """
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
                if len(date_str) == 10:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                if start <= record_date <= end:
                    return True
            except ValueError:
                continue

    return False


def should_continue_paging(records: List[Dict[str, Any]], start_date: str, end_date: str) -> bool:
    """
    检查是否需要继续翻页

    Args:
        records: 已抓取的记录列表
        start_date: 起始日期字符串
        end_date: 结束日期字符串

    Returns:
        bool: True表示需要继续翻页，False表示不需要
    """
    if not records:
        return True

    # 检查最后一条记录
    last_record = records[-1]
    return has_valid_date_in_range(last_record, start_date, end_date)


def has_next_page(page: Page) -> bool:
    """
    检查是否存在下一页

    Args:
        page: 页面对象

    Returns:
        bool: True表示存在下一页，False表示不存在
    """
    try:
        next_button = page.locator(".tic.tic-laydate-next-m")
        return next_button.count() > 0
    except Exception:
        return False


def turn_page(page: Page) -> bool:
    """
    执行翻页操作

    Args:
        page: 页面对象

    Returns:
        bool: True表示翻页成功，False表示翻页失败
    """
    try:
        # 等待翻页元素出现
        next_button = page.locator(".tic.tic-laydate-next-m")
        next_button.wait_for(state="visible", timeout=5000)

        # 点击翻页
        turn_result = run_step(
            next_button.click,
            step_name="点击下一页",
            critical=True,
            retries=1,
        )

        if not turn_result.ok:
            return False

        # 等待新页面加载完成
        wait_result = run_step(
            page.wait_for_load_state,
            "networkidle",
            step_name="等待新页面加载",
            critical=True,
            retries=2,
        )

        return wait_result.ok
    except Exception as e:
        logger.warning(f"[risk_2.paging] 翻页失败: {e}")
        return False

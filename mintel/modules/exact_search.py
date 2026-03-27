"""Apply exact search filters on the Mintel product list page."""

from __future__ import annotations

from typing import Protocol
import re

from loguru import logger
from playwright.sync_api import Page

from getdata1.modules.retry import run_with_timeout_retry


class WaitBeforeAction(Protocol):
    def __call__(self, page: Page, milliseconds: float | None = None) -> None: ...


def wait_for_search_results(page: Page, wait_before_action: WaitBeforeAction) -> int:
    """Wait until the search summary appears and return the current result count."""
    run_with_timeout_retry(
        "等待搜索结果统计出现",
        page,
        wait_before_action,
        lambda: page.locator("#products_search_count").wait_for(state="visible", timeout=15000),
    )
    result_count = get_search_result_count(page)
    if result_count > 0:
        run_with_timeout_retry(
            "等待搜索结果列表出现",
            page,
            wait_before_action,
            lambda: page.locator("#product_search_results").wait_for(state="visible", timeout=15000),
        )
    wait_before_action(page)
    return result_count


def apply_exact_search(page: Page, product_name: str, wait_before_action: WaitBeforeAction) -> int:
    """Apply the given exact product name search and return the current result count."""
    logger.info("执行精确搜索: {name}", name=product_name)
    search_box = page.get_by_role("textbox", name="精确搜索")
    create_search_button = page.get_by_role("button", name="创建搜索")

    def perform_exact_search() -> None:
        search_box.wait_for(timeout=15000)
        search_box.click()
        wait_before_action(page)
        search_box.fill(product_name)
        wait_before_action(page)
        create_search_button.click()

    run_with_timeout_retry("执行精确搜索动作", page, wait_before_action, perform_exact_search)
    result_count = wait_for_search_results(page, wait_before_action)
    logger.info("精确搜索结果条数: {count}", count=result_count)
    return result_count


def get_search_result_count(page: Page) -> int:
    """Read the current search result count from the summary area."""
    summary_text = page.locator("#products_search_count").inner_text().strip()
    match = re.search(r"([\d,]+)", summary_text)
    if match is None:
        return 0

    return int(match.group(1).replace(",", ""))

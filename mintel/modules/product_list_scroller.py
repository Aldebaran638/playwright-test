"""Scroll the Mintel product list page until new results appear."""

from __future__ import annotations

from typing import Protocol

from loguru import logger
from playwright.sync_api import Page

from getdata1.modules.product_list_reader import collect_visible_products


class WaitBeforeAction(Protocol):
    def __call__(self, page: Page, milliseconds: float | None = None) -> None: ...


def scroll_until_new_products(
    page: Page,
    seen_item_ids: set[str],
    wait_before_action: WaitBeforeAction,
    max_wait_rounds: int = 6,
) -> bool:
    """Scroll downward and wait until at least one unseen product appears."""
    logger.info("开始向下滚动并等待新列表项出现")
    for wait_round in range(1, max_wait_rounds + 1):
        page.mouse.wheel(0, 1800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        wait_before_action(page, 1200)

        loading = page.locator("#post_search_results_loading")
        if loading.count() > 0 and loading.is_visible():
            loading.wait_for(state="hidden", timeout=8000)

        visible_products = collect_visible_products(page)
        if any(product.item_id not in seen_item_ids for product in visible_products):
            logger.info("第 {round} 轮滚动后发现新列表项", round=wait_round)
            return True

    logger.warning("滚动 {rounds} 轮后仍未出现新的列表项", rounds=max_wait_rounds)
    return False

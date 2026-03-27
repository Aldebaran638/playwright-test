"""Read products from the Mintel product list page."""

from __future__ import annotations

from dataclasses import dataclass
import re

from loguru import logger
from playwright.sync_api import Page


ITEM_ID_PATTERN = re.compile(r"^item_(\d+)$")


@dataclass(frozen=True, slots=True)
class ProductListItem:
    item_id: str
    title: str


def collect_visible_products(page: Page) -> list[ProductListItem]:
    """Collect all currently visible product list items from the page."""
    products: list[ProductListItem] = []
    items = page.locator("li.list_view_item.product")

    for index in range(items.count()):
        item = items.nth(index)
        raw_id = item.get_attribute("id") or ""
        match = ITEM_ID_PATTERN.match(raw_id)
        if match is None:
            continue

        title_locator = item.locator(".product_description_header a").first
        if title_locator.count() == 0:
            continue

        title = _normalize_title(title_locator.inner_text())
        if not title:
            continue

        products.append(ProductListItem(item_id=match.group(1), title=title))

    logger.debug("当前页面可见列表项数量: {count}", count=len(products))
    return products


def collect_new_products(page: Page, seen_item_ids: set[str]) -> list[ProductListItem]:
    """Collect only the newly appeared product list items."""
    new_products: list[ProductListItem] = []

    for product in collect_visible_products(page):
        if product.item_id in seen_item_ids:
            continue
        seen_item_ids.add(product.item_id)
        new_products.append(product)

    logger.info("本次新增列表项数量: {count}", count=len(new_products))
    return new_products


def normalize_product_title(title: str) -> str:
    """Normalize product titles with only light whitespace cleanup."""
    return _normalize_title(title)


def _normalize_title(title: str) -> str:
    normalized = title.replace("\xa0", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()

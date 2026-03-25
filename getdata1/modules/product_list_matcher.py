"""Match products from the Mintel product list page."""

from __future__ import annotations

from getdata1.modules.product_list_reader import ProductListItem, normalize_product_title


def find_exact_match(products: list[ProductListItem], target_name: str) -> ProductListItem | None:
    """Return the product whose title matches the target name after light normalization."""
    normalized_target = normalize_product_title(target_name)
    for product in products:
        if product.title == normalized_target:
            return product
    return None

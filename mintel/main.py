import sys
from pathlib import Path
import re
import random

from loguru import logger
from playwright.sync_api import Page, Playwright, sync_playwright

# 允许直接运行当前脚本时，也能导入项目根目录下的模块。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from getdata1.modules import (
    apply_exact_search,
    collect_new_products,
    download_product_from_list,
    enter_product_list_page,
    find_exact_match,
    run_with_timeout_retry,
    scroll_until_new_products,
    wait_for_search_results,
)


MAX_EXPAND_ROUNDS = 5

# 名称列表请填写“列表页标题的精确原文”。
TARGET_PRODUCT_NAMES = [
    "Soothing Repair Cream pH 4.5",
    "Hydra + Soft Serve Intense Moisturizing Cream",
    "Night Power Bounce Creme",
]


def wait_before_action(page: Page, milliseconds: float | None = None) -> None:
    # 默认随机等待 0.5s 到 1.5s；显式传入时使用固定等待。
    wait_ms = milliseconds if milliseconds is not None else random.uniform(500, 1500)
    page.wait_for_timeout(wait_ms)


def clear_current_search_condition(page: Page, product_name: str) -> None:
    # 点击当前搜索条件标签里的删除链接，再等待结果列表刷新。
    logger.info("删除当前精确搜索条件: {name}", name=product_name)
    def remove_search_condition() -> None:
        search_label = page.locator("label").filter(has_text=re.compile(re.escape(product_name)))
        search_label.get_by_role("link").click()

    run_with_timeout_retry(
        f"删除精确搜索条件 {product_name}",
        page,
        wait_before_action,
        remove_search_condition,
    )
    wait_for_search_results(page, wait_before_action)
    page.evaluate("window.scrollTo(0, 0)")
    wait_before_action(page)


def run(playwright: Playwright) -> None:
    logger.info("启动 getdata1 主流程")
    context, product_list_page = enter_product_list_page(playwright, wait_before_action)

    found_names: list[str] = []
    missing_names: list[str] = []
    downloaded_files: list[Path] = []

    try:
        for name in TARGET_PRODUCT_NAMES:
            logger.info("开始处理名称: {name}", name=name)
            search_result_count = apply_exact_search(product_list_page, name, wait_before_action)
            if search_result_count == 0:
                logger.warning("精确搜索结果为 0，跳过当前名称: {name}", name=name)
                missing_names.append(name)
                clear_current_search_condition(product_list_page, name)
                continue

            seen_item_ids: set[str] = set()
            matched_item_id: str | None = None

            for search_round in range(1, MAX_EXPAND_ROUNDS + 1):
                logger.info("名称 {name} 进入第 {round} 轮搜索页扩展", name=name, round=search_round)
                new_products = collect_new_products(product_list_page, seen_item_ids)
                matched_product = find_exact_match(new_products, name)

                if matched_product is not None:
                    logger.info(
                        "找到精确匹配项: {title} (item_id={item_id})",
                        title=matched_product.title,
                        item_id=matched_product.item_id,
                    )
                    downloaded_path = download_product_from_list(
                        product_list_page,
                        matched_product.item_id,
                        PROJECT_ROOT / "downloads",
                        wait_before_action,
                    )
                    matched_item_id = matched_product.item_id
                    downloaded_files.append(downloaded_path)
                    found_names.append(name)
                    break

                has_new_products = scroll_until_new_products(
                    product_list_page,
                    seen_item_ids,
                    wait_before_action,
                )
                if not has_new_products:
                    break

            if matched_item_id is None:
                logger.warning(
                    "进行 {rounds} 次搜索页扩展后仍然没有找到符合的内容，请检查名字是否正确: {name}",
                    rounds=MAX_EXPAND_ROUNDS,
                    name=name,
                )
                missing_names.append(name)

            clear_current_search_condition(product_list_page, name)

        logger.info("找到的名称: {found}", found=found_names)
        logger.info("未找到的名称: {missing}", missing=missing_names)
        logger.info("下载文件列表: {downloads}", downloads=[str(path) for path in downloaded_files])
    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

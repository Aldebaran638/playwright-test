import re

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.common.run_step import run_step


def _split_tag_text(raw_text: str) -> tuple[str, str] | None:
    normalized_text = raw_text.strip()
    if not normalized_text:
        return None

    match = re.search(r"(.*?)(\d+)$", normalized_text)
    if match:
        label = match.group(1).strip()
        count = match.group(2)
        if label and not label.isdigit():
            return label, count
        return None

    if normalized_text.isdigit():
        return None

    return normalized_text, "0"


def extract_tag_nav_texts(page: Page) -> list[tuple[str, str]]:
    logger.info("[business_risk.tag_nav_extractor] 开始提取经营风险标签导航文本")

    wait_result = run_step(
        page.wait_for_selector,
        "#JS_tag_nav",
        timeout=5000,
        step_name="等待经营风险标签导航加载",
        critical=False,
        retries=1,
    )
    if not wait_result.ok:
        logger.warning("[business_risk.tag_nav_extractor] 未找到标签导航容器，返回空结果")
        return []

    raw_items_result = run_step(
        page.evaluate,
        """() => {
            const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
            return Array.from(document.querySelectorAll("#JS_tag_nav > *"))
                .map((item) => clean(item.innerText || item.textContent || ""))
                .filter(Boolean);
        }""",
        step_name="提取经营风险标签导航文本",
        critical=False,
        retries=0,
    )
    if not raw_items_result.ok or raw_items_result.value is None:
        logger.warning("[business_risk.tag_nav_extractor] 标签导航文本提取失败，返回空结果")
        return []

    result: list[tuple[str, str]] = []
    for raw_text in raw_items_result.value:
        parsed_item = _split_tag_text(str(raw_text))
        if parsed_item is not None:
            result.append(parsed_item)

    logger.info(f"[business_risk.tag_nav_extractor] 提取完成，标签数: {len(result)}")
    return result

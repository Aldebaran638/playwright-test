from playwright.async_api import Page

from zhy.modules.folder_table.models import TableSchema


def clean_schema_labels(labels: list[str]) -> list[str]:
    # 清理空列和无效列名，保留当前文件夹真正可用的表头文本。
    cleaned: list[str] = []
    for raw_label in labels:
        label = " ".join((raw_label or "").replace("\n", " ").split())
        if not label:
            continue
        if label in {"", "&nbsp;"}:
            continue
        cleaned.append(label)
    return cleaned


async def extract_schema_labels_from_title_attributes(
    page: Page,
    header_selector: str,
) -> list[str]:
    # 一些线上页面把字段名放在内部 title 属性里，而外层 colHeader 的 innerText 为空。
    title_locator = page.locator(f"{header_selector} .field-col-header [title]")
    labels: list[str] = []
    seen: set[str] = set()
    count = await title_locator.count()
    for index in range(count):
        raw_label = await title_locator.nth(index).get_attribute("title")
        label = " ".join((raw_label or "").replace("\n", " ").split())
        if not label:
            continue
        if label in {"&nbsp;", "新建自定义字段"}:
            continue
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


async def extract_table_schema(page: Page, selectors: dict[str, str]) -> TableSchema:
    # 动态读取当前文件夹的表头结构，避免把字段写死在代码里。
    header_selector = selectors["table_header_cells"]
    raw_labels = await page.locator(header_selector).all_inner_texts()
    labels = clean_schema_labels(raw_labels)
    if not labels:
        labels = await extract_schema_labels_from_title_attributes(page, header_selector)
    if not labels:
        raise ValueError("failed to extract table schema from current folder")

    return TableSchema(columns=labels, column_count=len(labels))

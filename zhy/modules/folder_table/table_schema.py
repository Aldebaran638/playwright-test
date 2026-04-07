from playwright.async_api import Page

from zhy.modules.folder_table.models import TableSchema


def clean_schema_labels(labels: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw_label in labels:
        label = " ".join((raw_label or "").replace("\n", " ").split())
        if not label:
            continue
        if label in {"", "&nbsp;"}:
            continue
        cleaned.append(label)
    return cleaned


async def extract_table_schema(page: Page, selectors: dict[str, str]) -> TableSchema:
    header_selector = selectors["table_header_cells"]
    raw_labels = await page.locator(header_selector).all_inner_texts()
    labels = clean_schema_labels(raw_labels)
    if not labels:
        raise ValueError("failed to extract table schema from current folder")

    return TableSchema(columns=labels, column_count=len(labels))

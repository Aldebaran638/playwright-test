import hashlib

from playwright.async_api import Locator, Page

from zhy.modules.folder_table.models import TableRowRecord, TableSchema


def normalize_cell_text(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split())


def build_row_key(row_data: dict[str, str]) -> str:
    first_non_empty = next((value for value in row_data.values() if value), "")
    if first_non_empty:
        return first_non_empty
    digest = hashlib.sha1(repr(sorted(row_data.items())).encode("utf-8")).hexdigest()
    return digest[:16]


def map_row_cells_to_schema(schema: TableSchema, cell_values: list[str]) -> dict[str, str]:
    row_data: dict[str, str] = {}
    for index, column in enumerate(schema.columns):
        row_data[column] = cell_values[index] if index < len(cell_values) else ""
    return row_data


async def page_has_rows(page: Page, selectors: dict[str, str]) -> bool:
    row_selector = selectors["table_row_selector"]
    return await page.locator(row_selector).count() > 0


async def _extract_row_cell_values(row: Locator) -> list[str]:
    cell_locator = row.locator("td")
    cell_count = await cell_locator.count()
    values: list[str] = []
    for index in range(cell_count):
        cell_text = await cell_locator.nth(index).inner_text()
        values.append(normalize_cell_text(cell_text))
    return values


async def extract_visible_rows(
    page: Page,
    folder_id: str,
    page_number: int,
    schema: TableSchema,
    selectors: dict[str, str],
) -> list[TableRowRecord]:
    row_selector = selectors["table_row_selector"]
    row_locator = page.locator(row_selector)
    row_count = await row_locator.count()
    results: list[TableRowRecord] = []

    for index in range(row_count):
        row = row_locator.nth(index)
        cell_values = await _extract_row_cell_values(row)
        row_data = map_row_cells_to_schema(schema, cell_values)
        row_key = build_row_key(row_data)
        results.append(
            TableRowRecord(
                folder_id=folder_id,
                page_number=page_number,
                row_key=row_key,
                data=row_data,
            )
        )

    return results

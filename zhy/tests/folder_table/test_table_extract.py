import asyncio
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.models import TableSchema
from zhy.modules.folder_table.table_extract import (
    build_row_key,
    extract_visible_rows,
    map_row_cells_to_schema,
    normalize_cell_text,
    page_has_rows,
)
from zhy.tests.folder_table.fixture_html_helpers import (
    extract_fixture_header_titles,
    extract_row_cell_texts,
    extract_visible_row_indexes,
    load_html_fixture,
)


class _FakeTextLocator:
    def __init__(self, text: str) -> None:
        self._text = text

    async def inner_text(self) -> str:
        return self._text


class _FakeCellListLocator:
    def __init__(self, cell_values: list[str]) -> None:
        self._cell_values = cell_values

    async def count(self) -> int:
        return len(self._cell_values)

    def nth(self, index: int) -> _FakeTextLocator:
        return _FakeTextLocator(self._cell_values[index])


class _FakeRowLocator:
    def __init__(self, cell_values: list[str]) -> None:
        self._cell_values = cell_values

    def locator(self, selector: str) -> _FakeCellListLocator:
        if selector != "td":
            raise AssertionError(f"unexpected selector: {selector}")
        return _FakeCellListLocator(self._cell_values)


class _FakeRowListLocator:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    async def count(self) -> int:
        return len(self._rows)

    def nth(self, index: int) -> _FakeRowLocator:
        return _FakeRowLocator(self._rows[index])


class _FakePage:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    def locator(self, selector: str) -> _FakeRowListLocator:
        if selector != ".fixture-row":
            raise AssertionError(f"unexpected selector: {selector}")
        return _FakeRowListLocator(self._rows)


class TestTableExtract(unittest.TestCase):
    def test_normalize_cell_text_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_cell_text(" CN105 \n 859882B "), "CN105 859882B")

    def test_map_row_cells_to_schema_uses_current_folder_columns(self) -> None:
        schema = TableSchema(columns=["public_no", "title", "legal_status"], column_count=3)
        row_data = map_row_cells_to_schema(schema, ["CN1", "title-a", "granted"])
        self.assertEqual(
            row_data,
            {"public_no": "CN1", "title": "title-a", "legal_status": "granted"},
        )

    def test_build_row_key_prefers_first_non_empty_value(self) -> None:
        key = build_row_key({"public_no": "CN1", "title": "title-a"})
        self.assertEqual(key, "CN1")

    def test_mid3_fixture_exposes_visible_rows_for_offline_tests(self) -> None:
        html_text = load_html_fixture("mid3.html")
        row_indexes = extract_visible_row_indexes(html_text)

        self.assertEqual(row_indexes[0], 0)
        self.assertEqual(row_indexes[-1], 49)
        self.assertEqual(len(row_indexes), 50)

    def test_mid3_fixture_first_row_maps_back_to_current_folder_schema(self) -> None:
        html_text = load_html_fixture("mid3.html")
        schema = TableSchema(columns=extract_fixture_header_titles(html_text), column_count=6)
        row_cells = extract_row_cell_texts(html_text, row_index=0)
        row_data = map_row_cells_to_schema(schema, row_cells)

        self.assertEqual(len(row_cells), 6)
        self.assertEqual(build_row_key(row_data), row_cells[0])
        self.assertIn("CN105859882B", row_cells[0])
        self.assertIn("2016-04-13", row_cells[3])
        self.assertIn("CN201610228315.0", row_cells[5])

    def test_extract_visible_rows_accepts_fixture_derived_row_data(self) -> None:
        html_text = load_html_fixture("mid3.html")
        schema = TableSchema(columns=extract_fixture_header_titles(html_text), column_count=6)
        first_row = extract_row_cell_texts(html_text, row_index=0)
        second_row = extract_row_cell_texts(html_text, row_index=1)
        fake_page = _FakePage(rows=[first_row, second_row])

        rows = asyncio.run(
            extract_visible_rows(
                page=fake_page,
                folder_id="folder-1",
                page_number=1,
                schema=schema,
                selectors={"table_row_selector": ".fixture-row"},
            )
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].folder_id, "folder-1")
        self.assertEqual(rows[0].page_number, 1)
        self.assertEqual(rows[0].row_key, first_row[0])
        self.assertEqual(rows[1].data[schema.columns[0]], second_row[0])

    def test_page_has_rows_detects_fixture_backed_rows(self) -> None:
        fake_page = _FakePage(rows=[["CN1", "title-a"]])

        has_rows = asyncio.run(page_has_rows(fake_page, {"table_row_selector": ".fixture-row"}))

        self.assertTrue(has_rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)

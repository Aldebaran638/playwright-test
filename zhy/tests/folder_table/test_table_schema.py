import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.table_schema import (
    clean_schema_labels,
    extract_schema_labels_from_title_attributes,
    extract_table_schema,
)
from zhy.tests.folder_table.fixture_html_helpers import extract_fixture_header_titles, load_html_fixture


class _FakeHeaderLocator:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    async def all_inner_texts(self) -> list[str]:
        return list(self._values)


class _FakeTitleLocatorItem:
    def __init__(self, title: str) -> None:
        self._title = title

    async def get_attribute(self, name: str) -> str | None:
        if name != "title":
            return None
        return self._title


class _FakeTitleLocator:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    async def count(self) -> int:
        return len(self._values)

    def nth(self, index: int) -> _FakeTitleLocatorItem:
        return _FakeTitleLocatorItem(self._values[index])


class _FakeSchemaPage:
    def __init__(self, mapping: dict[str, object]) -> None:
        self._mapping = mapping

    def locator(self, selector: str):
        try:
            return self._mapping[selector]
        except KeyError as exc:
            raise AssertionError(f"unexpected selector: {selector}") from exc


class TestTableSchema(unittest.TestCase):
    def test_clean_schema_labels_filters_empty_labels(self) -> None:
        labels = clean_schema_labels(["", "  public_no  ", "\ntitle\n", "&nbsp;", "legal_status"])
        self.assertEqual(labels, ["public_no", "title", "legal_status"])

    def test_mid3_fixture_contains_current_folder_schema_titles(self) -> None:
        html_text = load_html_fixture("mid3.html")
        labels = clean_schema_labels(extract_fixture_header_titles(html_text))

        self.assertEqual(len(labels), 6)
        self.assertTrue(all(label for label in labels))

    def test_extract_table_schema_accepts_fixture_derived_headers(self) -> None:
        html_text = load_html_fixture("mid2.html")
        header_values = extract_fixture_header_titles(html_text)
        fake_page = Mock()
        fake_page.locator.return_value = _FakeHeaderLocator(header_values)

        schema = asyncio.run(
            extract_table_schema(fake_page, {"table_header_cells": ".fixture-header"})
        )

        self.assertEqual(schema.column_count, 6)
        self.assertEqual(len(schema.columns), 6)
        self.assertTrue(all(column for column in schema.columns))

    def test_extract_schema_labels_from_title_attributes_supports_title_fallback(self) -> None:
        fake_page = _FakeSchemaPage(
            {
                ".fixture-header .field-col-header [title]": _FakeTitleLocator(
                    ["公开(公告)号", "申请号", "申请日", "公开(公告)日", "独立权利要求", "新建自定义字段"]
                )
            }
        )

        labels = asyncio.run(
            extract_schema_labels_from_title_attributes(fake_page, ".fixture-header")
        )

        self.assertEqual(labels, ["公开(公告)号", "申请号", "申请日", "公开(公告)日", "独立权利要求"])

    def test_extract_table_schema_falls_back_to_title_attributes_when_inner_text_empty(self) -> None:
        fake_page = _FakeSchemaPage(
            {
                ".fixture-header": _FakeHeaderLocator(["", "", ""]),
                ".fixture-header .field-col-header [title]": _FakeTitleLocator(
                    ["公开(公告)号", "申请号", "申请日"]
                ),
            }
        )

        schema = asyncio.run(extract_table_schema(fake_page, {"table_header_cells": ".fixture-header"}))

        self.assertEqual(schema.columns, ["公开(公告)号", "申请号", "申请日"])
        self.assertEqual(schema.column_count, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)

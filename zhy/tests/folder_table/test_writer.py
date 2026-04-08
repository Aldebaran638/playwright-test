import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.models import FolderTarget, TableRowRecord, TableSchema
from zhy.modules.folder_table.writer import (
    append_debug,
    append_failure,
    append_rows,
    get_folder_output_dir,
    write_meta,
    write_schema,
)
from zhy.tests.folder_table.fixture_html_helpers import extract_fixture_header_titles, load_html_fixture


class TestWriter(unittest.TestCase):
    def test_writer_outputs_are_separated_by_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = FolderTarget(space_id="space-1", folder_id="folder-2", base_url="https://example.com")
            output_dir = get_folder_output_dir(root, target)

            schema = TableSchema(columns=["public_no", "title"], column_count=2)
            rows = [
                TableRowRecord(
                    folder_id="folder-2",
                    page_number=1,
                    row_key="CN1",
                    data={"public_no": "CN1", "title": "title-a"},
                )
            ]

            schema_path = write_schema(output_dir, schema)
            rows_path = append_rows(output_dir, rows)
            meta_path = write_meta(output_dir, {"folder_id": "folder-2"})

            self.assertTrue(schema_path.exists())
            self.assertTrue(rows_path.exists())
            self.assertTrue(meta_path.exists())
            self.assertEqual(json.loads(schema_path.read_text(encoding="utf-8"))["column_count"], 2)

    def test_writer_appends_rows_without_overwriting_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = FolderTarget(space_id="space-1", folder_id="folder-2", base_url="https://example.com")
            output_dir = get_folder_output_dir(root, target)
            first_batch = [
                TableRowRecord(
                    folder_id="folder-2",
                    page_number=1,
                    row_key="CN1",
                    data={"public_no": "CN1", "title": "title-a"},
                )
            ]
            second_batch = [
                TableRowRecord(
                    folder_id="folder-2",
                    page_number=2,
                    row_key="CN2",
                    data={"public_no": "CN2", "title": "title-b"},
                )
            ]

            rows_path = append_rows(output_dir, first_batch)
            append_rows(output_dir, second_batch)

            lines = rows_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["row_key"], "CN1")
            self.assertEqual(json.loads(lines[1])["row_key"], "CN2")

    def test_writer_can_persist_fixture_derived_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "space-1" / "folder-2"
            html_text = load_html_fixture("mid3.html")
            columns = extract_fixture_header_titles(html_text)
            schema = TableSchema(columns=columns, column_count=len(columns))

            schema_path = write_schema(output_dir, schema)
            payload = json.loads(schema_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["column_count"], 6)
            self.assertEqual(payload["columns"], columns)

    def test_append_failure_persists_error_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "space-1" / "folder-2"

            failures_path = append_failure(
                output_dir,
                {
                    "folder_id": "folder-2",
                    "page_number": 4,
                    "error_message": "failed to extract table schema after buffer wait",
                },
            )

            lines = failures_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["page_number"], 4)

    def test_append_debug_persists_debug_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "space-1" / "folder-2"

            debug_path = append_debug(
                output_dir,
                {
                    "folder_id": "folder-2",
                    "requested_page_number": 1,
                    "status": "success",
                    "header_text_preview": ["公开号", "申请号"],
                    "first_row_preview": ["CN1", "CN2025"],
                },
            )

            lines = debug_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["requested_page_number"], 1)
            self.assertEqual(payload["header_text_preview"], ["公开号", "申请号"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

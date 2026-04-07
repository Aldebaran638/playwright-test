import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.models import FolderTarget, TableRowRecord, TableSchema
from zhy.modules.folder_table.writer import append_rows, get_folder_output_dir, write_meta, write_schema


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


if __name__ == "__main__":
    unittest.main(verbosity=2)

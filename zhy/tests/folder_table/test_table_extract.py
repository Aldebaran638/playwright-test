import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.models import TableSchema
from zhy.modules.folder_table.table_extract import build_row_key, map_row_cells_to_schema, normalize_cell_text


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


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.folder_table_workflow import _merge_rows_by_key
from zhy.modules.folder_table.models import TableRowRecord
from zhy.modules.folder_table.table_scroll import ScrollSnapshot, is_scroll_stable


class TestFolderTableWorkflow(unittest.TestCase):
    def test_merge_rows_by_key_deduplicates_same_row_key(self) -> None:
        rows_by_key = {}
        first = TableRowRecord(folder_id="folder-1", page_number=1, row_key="CN1", data={"public_no": "CN1"})
        second = TableRowRecord(folder_id="folder-1", page_number=1, row_key="CN1", data={"public_no": "CN1"})

        changed_first = _merge_rows_by_key(rows_by_key, [first])
        changed_second = _merge_rows_by_key(rows_by_key, [second])

        self.assertTrue(changed_first)
        self.assertFalse(changed_second)
        self.assertEqual(len(rows_by_key), 1)

    def test_is_scroll_stable_checks_scroll_metrics(self) -> None:
        previous = ScrollSnapshot(top=100, height=1000, client_height=500)
        current = ScrollSnapshot(top=100, height=1000, client_height=500)
        self.assertTrue(is_scroll_stable(previous, current))


if __name__ == "__main__":
    unittest.main(verbosity=2)

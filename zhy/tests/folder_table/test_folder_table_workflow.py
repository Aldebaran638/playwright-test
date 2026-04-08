import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.folder_table_workflow import (
    _build_running_meta,
    _collect_new_rows_by_key,
    _merge_rows_by_key,
    _resolve_redirected_page_number,
)
from zhy.modules.folder_table.models import FolderTarget, PageCollectResult, TableRowRecord, TableSchema
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

    def test_collect_new_rows_by_key_returns_only_new_rows(self) -> None:
        existing = TableRowRecord(folder_id="folder-1", page_number=1, row_key="CN1", data={"public_no": "CN1"})
        duplicate = TableRowRecord(folder_id="folder-1", page_number=2, row_key="CN1", data={"public_no": "CN1"})
        fresh = TableRowRecord(folder_id="folder-1", page_number=2, row_key="CN2", data={"public_no": "CN2"})
        rows_by_key = {existing.row_key: existing}

        new_rows = _collect_new_rows_by_key(rows_by_key, [duplicate, fresh])

        self.assertEqual([row.row_key for row in new_rows], ["CN2"])
        self.assertEqual(sorted(rows_by_key.keys()), ["CN1", "CN2"])

    def test_resolve_redirected_page_number_detects_page_mismatch(self) -> None:
        current_url = "https://workspace.zhihuiya.com/detail/patent/table?spaceId=space-1&folderId=folder-2&page=1"

        self.assertEqual(_resolve_redirected_page_number(2, current_url), 1)
        self.assertIsNone(_resolve_redirected_page_number(1, current_url))

    def test_build_running_meta_contains_progress_fields(self) -> None:
        target = FolderTarget(
            space_id="space-1",
            folder_id="folder-2",
            base_url="https://workspace.zhihuiya.com/detail/patent/table?spaceId=space-1&folderId=folder-2&page=1",
        )
        schema = TableSchema(columns=["public_no"], column_count=1)
        row = TableRowRecord(folder_id="folder-2", page_number=1, row_key="CN1", data={"public_no": "CN1"})

        meta = _build_running_meta(
            target=target,
            schema=schema,
            collected_page_numbers=[1, 3],
            all_rows_by_key={row.row_key: row},
            first_empty_page=4,
            failed_pages=[2],
            failure_details={2: "timeout"},
            status="running",
        )

        self.assertEqual(meta["status"], "running")
        self.assertEqual(meta["total_pages_collected"], 2)
        self.assertEqual(meta["total_rows_collected"], 1)
        self.assertEqual(meta["failed_page_numbers"], [2])
        self.assertEqual(meta["failure_details"]["2"], "timeout")
        self.assertEqual(meta["empty_page_number"], 4)
        self.assertEqual(meta["schema"]["column_count"], 1)

    def test_page_collect_result_can_represent_empty_state(self) -> None:
        result = PageCollectResult(
            folder_id="folder-1",
            page_number=5,
            status="empty",
            schema=None,
            rows=[],
            is_empty=True,
            error_message=None,
        )

        self.assertEqual(result.status, "empty")
        self.assertTrue(result.is_empty)
        self.assertEqual(result.rows, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

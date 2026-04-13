import sys
import unittest
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.competitor_patent_pipeline.monthly_fetch import (
    build_monthly_patents_request_body,
    filter_folder_items_for_test,
    filter_patents_for_target_month,
    get_page_publication_date_bounds,
    parse_month_bounds,
)


class TestCompetitorPatentPipelineMonthlyFetch(unittest.TestCase):
    def test_parse_month_bounds_returns_half_open_range(self) -> None:
        month_start, next_month_start = parse_month_bounds("2026-04")

        self.assertEqual(month_start, date(2026, 4, 1))
        self.assertEqual(next_month_start, date(2026, 5, 1))

    def test_filter_patents_for_target_month_keeps_only_matching_pbd(self) -> None:
        rows = [
            {"PATENT_ID": "too-new", "PBD": "2026-05-03"},
            {"PATENT_ID": "match-1", "PBD": "2026-04-25"},
            {"PATENT_ID": "match-2", "PBD": "2026-04-01"},
            {"PATENT_ID": "too-old", "PBD": "2026-03-31"},
            {"PATENT_ID": "invalid", "PBD": ""},
        ]

        matched = filter_patents_for_target_month(rows, date(2026, 4, 1), date(2026, 5, 1))

        self.assertEqual([row["PATENT_ID"] for row in matched], ["match-1", "match-2"])

    def test_get_page_publication_date_bounds_returns_newest_and_oldest(self) -> None:
        rows = [
            {"PBD": "2026-04-25"},
            {"PBD": "2026-04-10"},
            {"PBD": "2026-03-30"},
        ]

        newest, oldest = get_page_publication_date_bounds(rows)

        self.assertEqual(newest, date(2026, 4, 25))
        self.assertEqual(oldest, date(2026, 3, 30))

    def test_build_monthly_patents_request_body_overrides_sort_and_page_fields(self) -> None:
        template = {
            "space_id": "old-space",
            "folder_id": "old-folder",
            "page": "9",
            "sort": "wtasc",
            "view_type": "whatever",
            "is_init": False,
            "standard_only": True,
        }

        body = build_monthly_patents_request_body(
            template,
            space_id="space-1",
            folder_id="folder-1",
            page=2,
            size=100,
            sort="pdesc",
            view_type="tablelist",
            is_init=True,
            standard_only=False,
        )

        self.assertEqual(body["space_id"], "space-1")
        self.assertEqual(body["folder_id"], "folder-1")
        self.assertEqual(body["page"], "2")
        self.assertEqual(body["size"], 100)
        self.assertEqual(body["sort"], "pdesc")
        self.assertEqual(body["view_type"], "tablelist")
        self.assertTrue(body["is_init"])
        self.assertFalse(body["standard_only"])

    def test_filter_folder_items_for_test_keeps_only_whitelist(self) -> None:
        folder_items = [
            {"folder_id": "a", "folder_name": "甲"},
            {"folder_id": "b", "folder_name": "乙"},
            {"folder_id": "c", "folder_name": "丙"},
        ]

        filtered = filter_folder_items_for_test(folder_items, ["b", "c"])

        self.assertEqual([item["folder_id"] for item in filtered], ["b", "c"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

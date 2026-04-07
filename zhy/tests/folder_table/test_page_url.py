import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.page_url import build_folder_page_url, parse_folder_target


class TestPageUrl(unittest.TestCase):
    def test_parse_folder_target_extracts_space_and_folder_ids(self) -> None:
        url = "https://workspace.zhihuiya.com/detail/patent/table?spaceId=space-1&folderId=folder-2&page=9"
        target = parse_folder_target(url)

        self.assertEqual(target.space_id, "space-1")
        self.assertEqual(target.folder_id, "folder-2")

    def test_build_folder_page_url_replaces_page_parameter(self) -> None:
        url = "https://workspace.zhihuiya.com/detail/patent/table?spaceId=space-1&folderId=folder-2&page=9"
        new_url = build_folder_page_url(url, 3)

        self.assertIn("page=3", new_url)
        self.assertIn("spaceId=space-1", new_url)
        self.assertIn("folderId=folder-2", new_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)

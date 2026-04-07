import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.page_size import is_expected_page_size_text, normalize_page_size_text


class TestPageSize(unittest.TestCase):
    def test_normalize_page_size_text_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_page_size_text(" 100   / per page "), "100 / per page")

    def test_is_expected_page_size_text_accepts_expected_value(self) -> None:
        self.assertTrue(is_expected_page_size_text("100 / per page", 100))

    def test_is_expected_page_size_text_rejects_other_value(self) -> None:
        self.assertFalse(is_expected_page_size_text("50 / per page", 100))


if __name__ == "__main__":
    unittest.main(verbosity=2)

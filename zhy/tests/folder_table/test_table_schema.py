import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table.table_schema import clean_schema_labels


class TestTableSchema(unittest.TestCase):
    def test_clean_schema_labels_filters_empty_labels(self) -> None:
        labels = clean_schema_labels(["", "  public_no  ", "\ntitle\n", "&nbsp;", "legal_status"])
        self.assertEqual(labels, ["public_no", "title", "legal_status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

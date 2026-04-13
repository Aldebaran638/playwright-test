import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.competitor_patent_report.models import CompetitorPatentReportConfig
from zhy.modules.competitor_patent_report.report_builder import (
    collect_report_rows,
    make_report_title,
    write_report_xlsx,
)


class TestCompetitorPatentReportBuilder(unittest.TestCase):
    def build_temp_config(self, root: Path) -> CompetitorPatentReportConfig:
        original_root = root / "original"
        enriched_root = root / "enriched"
        original_folder = original_root / "space_folder1"
        enriched_folder = enriched_root / "space_folder1"
        original_folder.mkdir(parents=True, exist_ok=True)
        enriched_folder.mkdir(parents=True, exist_ok=True)

        page_payload = {
            "data": {
                "patents_data": [
                    {
                        "PATENT_ID": "pat-1",
                        "TITLE": "标题一",
                        "ANCS": ["公司A", "公司B"],
                        "IN": ["发明人甲", "发明人乙"],
                        "APN": "APN-001",
                        "PN": "PN-001",
                        "APD": "2026-04-02",
                        "PBD": "2026-04-15",
                        "LEGAL_STATUS": [3, 61],
                    },
                    {
                        "PATENT_ID": "pat-2",
                        "TITLE": "标题二",
                        "ANCS": ["公司C"],
                        "IN": ["发明人丙"],
                        "APD": "2026-03-01",
                        "PBD": "2026-03-20",
                        "LEGAL_STATUS": [16],
                    },
                ]
            }
        }
        enriched_payload = {
            "records": [
                {"PATENT_ID": "pat-1", "ABST": "技术方案一", "ISD": "2026-04-20"},
                {"PATENT_ID": "pat-2", "ABST": "技术方案二", "ISD": ""},
            ]
        }
        folder_mapping_payload = {
            "data": [
                {"folder_id": "folder1", "folder_name": "竞争对手甲"},
            ]
        }
        legal_status_payload = {
            "data": {
                "legalStatus": {
                    "3": {"title": {"cn": "授权"}},
                    "61": {"title": {"cn": "有效"}},
                    "16": {"title": {"cn": "未缴年费"}},
                }
            }
        }

        (original_folder / "page_0001.json").write_text(json.dumps(page_payload, ensure_ascii=False), encoding="utf-8")
        (enriched_folder / "page_0001.json").write_text(json.dumps(enriched_payload, ensure_ascii=False), encoding="utf-8")
        (root / "mid3.json").write_text(json.dumps(folder_mapping_payload, ensure_ascii=False), encoding="utf-8")
        (root / "mid1.json").write_text(json.dumps(legal_status_payload, ensure_ascii=False), encoding="utf-8")

        return CompetitorPatentReportConfig(
            month="2026-04",
            original_root=original_root,
            enriched_root=enriched_root,
            folder_mapping_file=root / "mid3.json",
            legal_status_mapping_file=root / "mid1.json",
            output_dir=root / "output",
        )

    def test_collect_report_rows_filters_by_month_and_maps_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.build_temp_config(Path(temp_dir))
            rows = collect_report_rows(config)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.sequence, 1)
        self.assertEqual(row.competitor_name, "竞争对手甲")
        self.assertEqual(row.applicant_or_patentee, "公司A；公司B")
        self.assertEqual(row.inventors, "发明人甲；发明人乙")
        self.assertEqual(row.application_or_publication_number, "APN-001")
        self.assertEqual(row.authorization_date, "2026-04-20")
        self.assertEqual(row.legal_status_text, "授权；有效")
        self.assertEqual(row.technical_solution, "技术方案一")

    def test_write_report_xlsx_contains_merge_cells(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.xlsx"
            rows = [
                __import__("copy").copy(
                    type("Row", (), {})()
                )
            ]

        # 用真实 dataclass 行对象测试 xlsx 结构。
        rows = []
        from zhy.modules.competitor_patent_report.models import CompetitorPatentReportRow

        rows.append(
            CompetitorPatentReportRow(
                sequence=1,
                competitor_name="竞争对手甲",
                invention_title="标题一",
                applicant_or_patentee="公司A；公司B",
                inventors="发明人甲；发明人乙",
                application_or_publication_number="APN-001",
                application_date="2026-04-02",
                publication_date="2026-04-15",
                authorization_date="2026-04-20",
                legal_status_text="授权；有效",
                technical_solution="技术方案一",
                source_folder_id="folder1",
                source_page_file="page_0001.json",
            )
        )
        rows.append(
            CompetitorPatentReportRow(
                sequence=2,
                competitor_name="竞争对手甲",
                invention_title="标题二",
                applicant_or_patentee="公司C",
                inventors="发明人丙",
                application_or_publication_number="APN-002",
                application_date="2026-04-05",
                publication_date="2026-04-18",
                authorization_date="/",
                legal_status_text="未缴年费",
                technical_solution="技术方案二",
                source_folder_id="folder1",
                source_page_file="page_0002.json",
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.xlsx"
            write_report_xlsx(output_path, make_report_title("2026-04"), rows)
            with zipfile.ZipFile(output_path, "r") as archive:
                sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")

        self.assertIn("A1:J1", sheet_xml)
        self.assertIn("B3:B4", sheet_xml)
        self.assertIn("竞争对手专利情报(2026年4月)", sheet_xml)


if __name__ == "__main__":
    unittest.main(verbosity=2)

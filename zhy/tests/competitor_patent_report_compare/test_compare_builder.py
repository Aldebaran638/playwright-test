import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.competitor_patent_report.report_builder import make_report_title, write_report_xlsx
from zhy.modules.competitor_patent_report.models import CompetitorPatentReportRow
from zhy.modules.competitor_patent_report_compare.compare_builder import (
    canonicalize_field_value,
    compare_report_records,
    build_markdown_report,
    load_report_records,
    run_competitor_patent_report_compare,
)
from zhy.modules.competitor_patent_report_compare.models import CompetitorPatentReportCompareConfig, ComparedPatentRecord


class TestCompetitorPatentReportCompareBuilder(unittest.TestCase):
    def build_rows(self, *, competitor_name: str, number: str, title: str, legal_status: str) -> list[CompetitorPatentReportRow]:
        return [
            CompetitorPatentReportRow(
                sequence=1,
                competitor_name=competitor_name,
                invention_title=title,
                applicant_or_patentee="公司A",
                inventors="发明人甲",
                application_or_publication_number=number,
                application_date="2026-04-01",
                publication_date="2026-04-15",
                authorization_date="/",
                legal_status_text=legal_status,
                technical_solution="技术方案",
                source_folder_id="folder1",
                source_page_file="page_0001.json",
            )
        ]

    def test_compare_report_records_detects_missing_and_different_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manual_path = temp_root / "manual.xlsx"
            generated_path = temp_root / "generated.xlsx"

            write_report_xlsx(
                manual_path,
                make_report_title("2026-04"),
                self.build_rows(competitor_name="竞争对手甲", number="APN-001", title="标题一", legal_status="授权"),
            )
            write_report_xlsx(
                generated_path,
                make_report_title("2026-04"),
                self.build_rows(competitor_name="竞争对手乙", number="APN-001", title="标题一", legal_status="有效"),
            )

            report_payload = compare_report_records(
                load_report_records(manual_path),
                load_report_records(generated_path),
            )

        self.assertEqual(report_payload["summary"]["shared_total"], 1)
        self.assertEqual(report_payload["summary"]["different_total"], 1)
        self.assertEqual(report_payload["different_records"][0]["competitor_name"], "竞争对手甲")
        self.assertEqual(report_payload["different_records"][0]["records"][0]["key"], "APN-001")
        self.assertEqual(len(report_payload["different_records"][0]["records"][0]["field_differences"]), 2)

    def test_run_competitor_patent_report_compare_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manual_path = temp_root / "manual.xlsx"
            generated_path = temp_root / "generated.xlsx"
            output_dir = temp_root / "output"

            write_report_xlsx(
                manual_path,
                make_report_title("2026-04"),
                self.build_rows(competitor_name="竞争对手甲", number="APN-001", title="标题一", legal_status="授权"),
            )
            write_report_xlsx(
                generated_path,
                make_report_title("2026-04"),
                self.build_rows(competitor_name="竞争对手甲", number="APN-002", title="标题二", legal_status="授权"),
            )

            config = CompetitorPatentReportCompareConfig(
                manual_report_path=manual_path,
                generated_report_path=generated_path,
                output_dir=output_dir,
                report_basename="diff_report",
            )
            markdown_path = run_competitor_patent_report_compare(config)

            json_path = output_dir / "diff_report.json"

            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("仅人工表存在", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("only_in_manual", json_path.read_text(encoding="utf-8"))

    def test_canonicalize_field_value_converts_excel_serial_date(self) -> None:
        self.assertEqual(canonicalize_field_value("申请日期", "45513"), "2024/8/9")

    def test_canonicalize_field_value_normalizes_equivalent_date_formats(self) -> None:
        self.assertEqual(canonicalize_field_value("申请日期", "2018/5/11"), "2018/5/11")
        self.assertEqual(canonicalize_field_value("申请日期", "2018-05-11"), "2018/5/11")

    def test_canonicalize_field_value_normalizes_competitor_aliases(self) -> None:
        self.assertEqual(canonicalize_field_value("主要竞争对手", "禾大"), canonicalize_field_value("主要竞争对手", "CRODA"))
        self.assertEqual(canonicalize_field_value("主要竞争对手", "ELC"), canonicalize_field_value("主要竞争对手", "雅诗兰黛"))

    def test_build_markdown_report_groups_missing_records_by_competitor(self) -> None:
        config = CompetitorPatentReportCompareConfig(
            manual_report_path=Path("manual.xlsx"),
            generated_report_path=Path("generated.xlsx"),
            output_dir=Path("output"),
            report_basename="diff",
        )
        payload = {
            "summary": {
                "manual_total": 2,
                "generated_total": 1,
                "shared_total": 0,
                "only_in_manual_total": 2,
                "only_in_generated_total": 1,
                "different_total": 0,
                "authorization_date_different_total": 0,
                "language_different_total": 0,
            },
            "only_in_manual": [
                {"key": "A", "row_number": 3, "competitor_name": "Ashland", "title": "标题一"},
                {"key": "B", "row_number": 4, "competitor_name": "Ashland", "title": "标题二"},
            ],
            "only_in_generated": [
                {"key": "C", "row_number": 5, "competitor_name": "Merck", "title": "标题三"},
            ],
            "different_records": [],
            "authorization_date_different_records": [],
            "language_different_records": [],
        }

        markdown = build_markdown_report(config, payload)

        self.assertIn("### Ashland", markdown)
        self.assertIn("### Merck", markdown)
        self.assertNotIn("人工主要竞争对手", markdown)

    def test_authorization_date_difference_moves_to_separate_section(self) -> None:
        manual_records = {
            "APN-001": ComparedPatentRecord(
                key="APN-001",
                fields={
                    "主要竞争对手": "Ashland",
                    "发明创造名称": "标题一",
                    "申请人/专利权人": "公司A",
                    "发明人": "发明人甲",
                    "申请号/专利号": "APN-001",
                    "申请日期": "2024/8/9",
                    "授权日期": "2026/2/11",
                    "法律状态": "授权",
                    "技术方案": "中文摘要",
                },
                source_row_number=3,
            )
        }
        generated_records = {
            "APN-001": ComparedPatentRecord(
                key="APN-001",
                fields={
                    "主要竞争对手": "Ashland",
                    "发明创造名称": "标题一",
                    "申请人/专利权人": "公司A",
                    "发明人": "发明人甲",
                    "申请号/专利号": "APN-001",
                    "申请日期": "2024/8/9",
                    "授权日期": "2026/2/12",
                    "法律状态": "授权",
                    "技术方案": "中文摘要",
                },
                source_row_number=4,
            )
        }

        payload = compare_report_records(manual_records, generated_records)
        config = CompetitorPatentReportCompareConfig(
            manual_report_path=Path("manual.xlsx"),
            generated_report_path=Path("generated.xlsx"),
            output_dir=Path("output"),
            report_basename="diff",
        )
        markdown = build_markdown_report(config, payload)

        self.assertEqual(payload["summary"]["different_total"], 0)
        self.assertEqual(payload["summary"]["authorization_date_different_total"], 1)
        self.assertEqual(payload["authorization_date_different_records"][0]["competitor_name"], "Ashland")
        self.assertEqual(
            payload["authorization_date_different_records"][0]["records"][0]["field_differences"][0]["field"],
            "授权日期",
        )
        self.assertIn("## 授权日期不一致", markdown)
        self.assertIn("字段：授权日期 | 人工表：2026/2/11 | 程序表：2026/2/12", markdown)

    def test_abstract_language_difference_only_reports_note(self) -> None:
        manual_records = {
            "APN-001": ComparedPatentRecord(
                key="APN-001",
                fields={
                    "主要竞争对手": "Ashland",
                    "发明创造名称": "标题一",
                    "申请人/专利权人": "公司A",
                    "发明人": "发明人甲",
                    "申请号/专利号": "APN-001",
                    "申请日期": "2024/8/9",
                    "授权日期": "/",
                    "法律状态": "授权",
                    "技术方案": "这是一段中文摘要",
                },
                source_row_number=3,
            )
        }
        generated_records = {
            "APN-001": ComparedPatentRecord(
                key="APN-001",
                fields={
                    "主要竞争对手": "Ashland",
                    "发明创造名称": "标题一",
                    "申请人/专利权人": "公司A",
                    "发明人": "发明人甲",
                    "申请号/专利号": "APN-001",
                    "申请日期": "2024/8/9",
                    "授权日期": "/",
                    "法律状态": "授权",
                    "技术方案": "This is an English abstract.",
                },
                source_row_number=4,
            )
        }

        payload = compare_report_records(manual_records, generated_records)
        config = CompetitorPatentReportCompareConfig(
            manual_report_path=Path("manual.xlsx"),
            generated_report_path=Path("generated.xlsx"),
            output_dir=Path("output"),
            report_basename="diff",
        )
        markdown = build_markdown_report(config, payload)

        self.assertEqual(payload["summary"]["different_total"], 0)
        self.assertEqual(payload["summary"]["authorization_date_different_total"], 0)
        self.assertEqual(payload["summary"]["language_different_total"], 1)
        self.assertEqual(payload["language_different_records"][0]["competitor_name"], "Ashland")
        self.assertEqual(payload["language_different_records"][0]["records"][0]["field_differences"][0]["field"], "技术方案")
        self.assertEqual(
            payload["language_different_records"][0]["records"][0]["field_differences"][0]["comparison_note"],
            "语言不同，暂不比较",
        )
        self.assertNotIn("## 共有但字段不同\n\n- `APN-001`", markdown)
        self.assertNotIn("## 授权日期不一致\n\n- `APN-001`", markdown)
        self.assertIn("## 语言不同暂不比较", markdown)
        self.assertIn("字段：技术方案 | 语言不同，暂不比较", markdown)
        self.assertNotIn("这是一段中文摘要", markdown)
        self.assertNotIn("This is an English abstract.", markdown)

    def test_chinese_and_japanese_abstracts_are_treated_as_different_languages(self) -> None:
        manual_records = {
            "APN-002": ComparedPatentRecord(
                key="APN-002",
                fields={
                    "主要竞争对手": "Ashland",
                    "发明创造名称": "标题二",
                    "申请人/专利权人": "公司A",
                    "发明人": "发明人甲",
                    "申请号/专利号": "APN-002",
                    "申请日期": "2024/8/9",
                    "授权日期": "/",
                    "法律状态": "授权",
                    "技术方案": "本发明公开了一种装置。",
                },
                source_row_number=5,
            )
        }
        generated_records = {
            "APN-002": ComparedPatentRecord(
                key="APN-002",
                fields={
                    "主要竞争对手": "Ashland",
                    "发明创造名称": "标题二",
                    "申请人/专利权人": "公司A",
                    "发明人": "发明人甲",
                    "申请号/专利号": "APN-002",
                    "申请日期": "2024/8/9",
                    "授权日期": "/",
                    "法律状态": "授权",
                    "技术方案": "放射線量測定処理を実施するための方法及び装置。",
                },
                source_row_number=6,
            )
        }

        payload = compare_report_records(manual_records, generated_records)

        self.assertEqual(payload["summary"]["language_different_total"], 1)
        self.assertEqual(payload["summary"]["different_total"], 0)
        self.assertEqual(
            payload["language_different_records"][0]["records"][0]["field_differences"][0]["comparison_note"],
            "语言不同，暂不比较",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

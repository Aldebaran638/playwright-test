import sys
import unittest
from pathlib import Path

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.company_risk.models import clean_risk_text, trim_risk_groups_by_count


logger.remove()
logger.add(sys.stdout, format="{message}")


class TestCompanyRiskModels(unittest.TestCase):
    def test_clean_risk_text_removes_html_tags(self) -> None:
        logger.info("[测试1] 验证 clean_risk_text() 会去掉 HTML 标签和多余空白")
        self.assertEqual(
            clean_risk_text("该公司曾因<em>买卖合同纠纷</em>而被起诉"),
            "该公司曾因买卖合同纠纷而被起诉",
        )

    def test_trim_risk_groups_by_count_stops_at_limit(self) -> None:
        logger.info("[测试2] 验证 trim_risk_groups_by_count() 会按 risk_count 累计到 10 为止")
        groups = [
            {
                "group_title": "裁判文书",
                "group_tag": "警示",
                "group_total_count": 15,
                "items": [
                    {"title": "A", "risk_count": 7, "desc": "裁判文书", "company_name": ""},
                    {"title": "B", "risk_count": 3, "desc": "裁判文书", "company_name": ""},
                    {"title": "C", "risk_count": 5, "desc": "裁判文书", "company_name": ""},
                ],
            }
        ]

        trimmed_groups, captured_count = trim_risk_groups_by_count(groups, max_capture_count=10)

        self.assertEqual(captured_count, 10)
        self.assertEqual(len(trimmed_groups[0]["items"]), 2)
        self.assertEqual([item["title"] for item in trimmed_groups[0]["items"]], ["A", "B"])

    def test_trim_risk_groups_by_count_keeps_first_large_item(self) -> None:
        logger.info("[测试3] 验证第一条本身超过上限时，仍会保留这一条内容")
        groups = [
            {
                "group_title": "开庭公告",
                "group_tag": "警示",
                "group_total_count": 15,
                "items": [
                    {"title": "A", "risk_count": 15, "desc": "开庭公告", "company_name": ""},
                    {"title": "B", "risk_count": 1, "desc": "开庭公告", "company_name": ""},
                ],
            }
        ]

        trimmed_groups, captured_count = trim_risk_groups_by_count(groups, max_capture_count=10)

        self.assertEqual(captured_count, 15)
        self.assertEqual(len(trimmed_groups[0]["items"]), 1)
        self.assertEqual(trimmed_groups[0]["items"][0]["title"], "A")


if __name__ == "__main__":
    unittest.main(verbosity=2)

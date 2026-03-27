import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tyc.modules.company_risk.collector as collector_module
from tyc.modules.company_risk.models import RiskNavigationResult, RiskSummaryItem


logger.remove()
logger.add(sys.stdout, format="{message}")


class FakeRiskPage:
    def __init__(self, url: str) -> None:
        self.url = url
        self._closed = False

    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True


class TestCompanyRiskCollector(unittest.TestCase):
    def test_collect_company_risk_returns_summary_when_all_zero(self) -> None:
        logger.info("[测试1] 验证没有可进入的风险入口时，collector 只返回风险概览")
        navigation_result = RiskNavigationResult(
            selected_risk_type=None,
            selected_risk_count=0,
            available_risks=[
                RiskSummaryItem(label="自身风险", count=0),
                RiskSummaryItem(label="周边风险", count=0),
                RiskSummaryItem(label="历史风险", count=0),
                RiskSummaryItem(label="预警提醒", count=0),
            ],
            should_collect=False,
        )

        with patch.object(
            collector_module,
            "open_first_available_risk_page",
            return_value=(navigation_result, None),
        ), patch.object(collector_module, "extract_company_risk_page") as extractor_mock:
            result = collector_module.collect_company_risk(page=object())  # type: ignore[arg-type]

        extractor_mock.assert_not_called()
        self.assertFalse(result["should_collect"])
        self.assertIsNone(result["risk_details"])

    def test_collect_company_risk_extracts_detail_and_closes_popup(self) -> None:
        logger.info("[测试2] 验证存在可进入的风险入口时，collector 会提取详情并关闭新页面")
        fake_risk_page = FakeRiskPage("https://www.tianyancha.com/risk")
        navigation_result = RiskNavigationResult(
            selected_risk_type="自身风险",
            selected_risk_count=285,
            available_risks=[RiskSummaryItem(label="自身风险", count=285)],
            should_collect=True,
        )

        with patch.object(
            collector_module,
            "open_first_available_risk_page",
            return_value=(navigation_result, fake_risk_page),
        ), patch.object(
            collector_module,
            "extract_company_risk_page",
            return_value={"risk_type": "自身风险", "captured_risk_count": 10},
        ):
            result = collector_module.collect_company_risk(page=object())  # type: ignore[arg-type]

        self.assertTrue(result["should_collect"])
        self.assertEqual(result["risk_page_url"], "https://www.tianyancha.com/risk")
        self.assertEqual(result["risk_details"]["captured_risk_count"], 10)
        self.assertTrue(fake_risk_page.is_closed())


if __name__ == "__main__":
    unittest.main(verbosity=2)

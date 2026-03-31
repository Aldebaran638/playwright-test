import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger
from playwright.sync_api import Browser, Playwright, sync_playwright


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tyc.modules.company_risk.page_extractor as extractor_module
from tyc.modules.run_step import StepResult


logger.remove()
logger.add(sys.stdout, format="{message}")


def build_success_step_result(fn, *args, **kwargs):
    kwargs.pop("step_name", None)
    kwargs.pop("critical", None)
    kwargs.pop("retries", None)
    return StepResult(ok=True, value=fn(*args, **kwargs), error=None)


class TestCompanyRiskPageExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("[测试1] 启动 Playwright 浏览器，准备测试 company_risk.page_extractor 模块")
        cls.playwright: Playwright = sync_playwright().start()
        cls.browser: Browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("[测试1] 关闭 Playwright 浏览器")
        cls.browser.close()
        cls.playwright.stop()

    def test_extract_company_risk_page_reads_mm_and_trims_by_risk_count(self) -> None:
        logger.info("[测试2] 验证风险页提取模块会解析 mm，并按 risk_count 上限截断到前 10")
        page = self.browser.new_page()
        page.set_content(
            """
            <div id="riskPage0" class="risk-block">
                <script>
                    var mm = {
                        "name":"自身风险",
                        "count":285,
                        "list":[
                            {
                                "total":21,
                                "tag":"警示",
                                "title":"裁判文书",
                                "list":[
                                    {"riskCount":7,"title":"该公司曾因<em>买卖合同纠纷</em>而被起诉","desc":"裁判文书","companyName":null},
                                    {"riskCount":3,"title":"该公司曾因<em>网络购物合同纠纷</em>而被起诉","desc":"裁判文书","companyName":null},
                                    {"riskCount":5,"title":"该公司曾因<em>名誉权纠纷</em>而被起诉","desc":"裁判文书","companyName":null}
                                ]
                            }
                        ]
                    }
                </script>
            </div>
            """,
            wait_until="domcontentloaded",
        )

        try:
            with patch.object(
                extractor_module,
                "run_step",
                side_effect=build_success_step_result,
            ):
                result = extractor_module.extract_company_risk_page(
                    page,
                    preferred_risk_type="自身风险",
                    max_capture_count=10,
                    source="inline-risk-page",
                )
        finally:
            page.close()

        self.assertEqual(result["risk_type"], "自身风险")
        self.assertEqual(result["total_risk_count"], 285)
        self.assertEqual(result["captured_risk_count"], 10)
        self.assertTrue(result["has_more"])
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual(len(result["groups"][0]["items"]), 2)
        self.assertEqual(
            result["groups"][0]["items"][0]["title"],
            "该公司曾因买卖合同纠纷而被起诉",
        )
        self.assertEqual(result["source"], "inline-risk-page")


if __name__ == "__main__":
    unittest.main(verbosity=2)

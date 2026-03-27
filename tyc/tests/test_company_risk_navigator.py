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

import tyc.modules.company_risk.navigator as navigator_module


logger.remove()
logger.add(sys.stdout, format="{message}")


class TestCompanyRiskNavigator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("[测试1] 启动 Playwright 浏览器，准备测试 company_risk.navigator 模块")
        cls.playwright: Playwright = sync_playwright().start()
        cls.browser: Browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("[测试1] 关闭 Playwright 浏览器")
        cls.browser.close()
        cls.playwright.stop()

    def test_open_first_available_risk_page_uses_first_non_zero_item(self) -> None:
        logger.info("[测试2] 验证风险入口扫描会按固定顺序点击第一个非零项")
        page = self.browser.new_page()
        page.set_content(
            """
            <div id="risk-summary">
                <div onclick="window.open('data:text/html,<html><body>risk-a</body></html>', '_blank')">
                    <div>自身风险</div><div>0</div>
                </div>
                <div onclick="window.open('data:text/html,<html><body>risk-b</body></html>', '_blank')">
                    <div>周边风险</div><div>4</div>
                </div>
                <div onclick="window.open('data:text/html,<html><body>risk-c</body></html>', '_blank')">
                    <div>历史风险</div><div>2</div>
                </div>
                <div onclick="window.open('data:text/html,<html><body>risk-d</body></html>', '_blank')">
                    <div>预警提醒</div><div>3</div>
                </div>
            </div>
            """,
            wait_until="domcontentloaded",
        )

        try:
            with patch.object(
                navigator_module,
                "run_step",
                side_effect=lambda action, step_name, **kwargs: action(),
            ):
                navigation_result, risk_page = navigator_module.open_first_available_risk_page(page)

            self.assertTrue(navigation_result.should_collect)
            self.assertEqual(navigation_result.selected_risk_type, "周边风险")
            self.assertEqual(navigation_result.selected_risk_count, 4)
            self.assertIsNotNone(risk_page)
            self.assertIn("risk-b", risk_page.content())
        finally:
            for popup_page in page.context.pages[1:]:
                popup_page.close()
            page.close()

    def test_open_first_available_risk_page_skips_click_when_all_zero(self) -> None:
        logger.info("[测试3] 验证四个风险入口都为 0 时不会再打开新页面")
        page = self.browser.new_page()
        page.set_content(
            """
            <div id="risk-summary">
                <div><div>自身风险</div><div>0</div></div>
                <div><div>周边风险</div><div>0</div></div>
                <div><div>历史风险</div><div>0</div></div>
                <div><div>预警提醒</div><div>0</div></div>
            </div>
            """,
            wait_until="domcontentloaded",
        )

        try:
            with patch.object(
                navigator_module,
                "run_step",
                side_effect=lambda action, step_name, **kwargs: action(),
            ):
                navigation_result, risk_page = navigator_module.open_first_available_risk_page(page)

            self.assertFalse(navigation_result.should_collect)
            self.assertIsNone(navigation_result.selected_risk_type)
            self.assertIsNone(risk_page)
            self.assertEqual(len(page.context.pages), 1)
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

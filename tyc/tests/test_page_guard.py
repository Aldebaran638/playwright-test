import sys
import unittest
from pathlib import Path

from loguru import logger
from playwright.sync_api import Browser, Playwright, sync_playwright


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.page_guard import NORMAL_PAGE, VERIFICATION_PAGE, check_page


logger.remove()
logger.add(sys.stdout, format="{message}")


class TestPageGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("[测试1] 启动 Playwright 浏览器，准备测试总检查模块")
        cls.playwright: Playwright = sync_playwright().start()
        cls.browser: Browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("[测试1] 关闭 Playwright 浏览器")
        cls.browser.close()
        cls.playwright.stop()

    def test_check_page_marks_verification_page_as_illegal(self) -> None:
        logger.info("[测试2] 验证总检查模块会把身份验证页判定为非法页面")
        page = self.browser.new_page()
        try:
            page.set_content(
                """
                <html>
                    <body>
                        <div>请进行身份验证以继续使用</div>
                    </body>
                </html>
                """,
                wait_until="domcontentloaded",
            )
            result = check_page(page)
        finally:
            page.close()

        self.assertTrue(result.is_illegal)
        self.assertEqual(result.page_type, VERIFICATION_PAGE)

    def test_check_page_marks_normal_page_as_normal(self) -> None:
        logger.info("[测试3] 验证总检查模块会把普通页面判定为正常页面")
        page = self.browser.new_page()
        try:
            page.set_content(
                """
                <html>
                    <body>
                        <div>这里是普通详情页内容</div>
                    </body>
                </html>
                """,
                wait_until="domcontentloaded",
            )
            result = check_page(page)
        finally:
            page.close()

        self.assertFalse(result.is_illegal)
        self.assertEqual(result.page_type, NORMAL_PAGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)

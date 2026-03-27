import sys
import unittest
from pathlib import Path

from loguru import logger
from playwright.sync_api import Browser, Playwright, sync_playwright


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.guards.verification_page import is_verification_page


logger.remove()
logger.add(sys.stdout, format="{message}")


class TestVerificationPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("[测试1] 启动 Playwright 浏览器，准备测试身份验证页识别模块")
        cls.playwright: Playwright = sync_playwright().start()
        cls.browser: Browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("[测试1] 关闭 Playwright 浏览器")
        cls.browser.close()
        cls.playwright.stop()

    def test_is_verification_page_matches_text_prompt(self) -> None:
        logger.info("[测试2] 验证模块能通过提示词识别身份验证页")
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
            self.assertTrue(is_verification_page(page))
        finally:
            page.close()

    def test_is_verification_page_matches_geetest_container(self) -> None:
        logger.info("[测试3] 验证模块能通过验证码容器识别身份验证页")
        page = self.browser.new_page()
        try:
            page.set_content(
                """
                <html>
                    <body>
                        <div class="geetest_captcha"></div>
                    </body>
                </html>
                """,
                wait_until="domcontentloaded",
            )
            self.assertTrue(is_verification_page(page))
        finally:
            page.close()

    def test_is_verification_page_returns_false_for_normal_page(self) -> None:
        logger.info("[测试4] 验证模块不会把普通页面误判为身份验证页")
        page = self.browser.new_page()
        try:
            page.set_content(
                """
                <html>
                    <body>
                        <div>这是正常公司详情页内容</div>
                    </body>
                </html>
                """,
                wait_until="domcontentloaded",
            )
            self.assertFalse(is_verification_page(page))
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

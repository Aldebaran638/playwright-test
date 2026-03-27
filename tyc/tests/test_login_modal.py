import sys
import unittest
from pathlib import Path

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.guards.login_modal import is_login_modal_page


logger.remove()
logger.add(sys.stdout, format="{message}")


class FakeLocator:
    def __init__(self, text: str = "", count: int = 0) -> None:
        self._text = text
        self._count = count

    def count(self) -> int:
        return self._count

    @property
    def first(self) -> "FakeLocator":
        return self

    def inner_text(self) -> str:
        return self._text


class FakePage:
    def __init__(self, *, body_text: str = "", selector_counts: dict[str, int] | None = None) -> None:
        self.body_text = body_text
        self.selector_counts = selector_counts or {}

    def locator(self, selector: str) -> FakeLocator:
        if selector == "body":
            return FakeLocator(self.body_text, 1 if self.body_text else 0)
        return FakeLocator("", self.selector_counts.get(selector, 0))


class TestLoginModal(unittest.TestCase):
    def test_is_login_modal_page_matches_key_texts(self) -> None:
        logger.info("[测试1] 验证登录弹窗模块能通过关键文案识别登录小界面")
        page = FakePage(
            body_text="扫码登录 登录即表示同意 用户协议 隐私政策",
        )
        self.assertTrue(is_login_modal_page(page))  # type: ignore[arg-type]

    def test_is_login_modal_page_matches_modal_selectors(self) -> None:
        logger.info("[测试2] 验证登录弹窗模块能通过弹窗结构选择器识别登录小界面")
        page = FakePage(
            selector_counts={
                "div[role='dialog'].tyc-modal": 1,
                ".login-main": 1,
            }
        )
        self.assertTrue(is_login_modal_page(page))  # type: ignore[arg-type]

    def test_is_login_modal_page_returns_false_for_normal_page(self) -> None:
        logger.info("[测试3] 验证普通页面不会被误判为登录弹窗")
        page = FakePage(body_text="这是正常的公司详情页内容")
        self.assertFalse(is_login_modal_page(page))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)

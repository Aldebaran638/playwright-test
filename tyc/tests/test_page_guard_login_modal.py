import sys
import unittest
from pathlib import Path

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.page_guard import LOGIN_MODAL_PAGE, NORMAL_PAGE, check_page


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


class TestPageGuardLoginModal(unittest.TestCase):
    def test_check_page_marks_login_modal_as_illegal(self) -> None:
        logger.info("[测试1] 验证总检查模块会把登录弹窗判定为非法页面")
        page = FakePage(
            body_text="扫码登录 登录即表示同意 用户协议 隐私政策",
            selector_counts={"div[role='dialog'].tyc-modal": 1},
        )

        result = check_page(page)  # type: ignore[arg-type]

        self.assertTrue(result.is_illegal)
        self.assertEqual(result.page_type, LOGIN_MODAL_PAGE)

    def test_check_page_keeps_normal_page_as_normal(self) -> None:
        logger.info("[测试2] 验证普通页面仍会被总检查模块判定为正常页面")
        page = FakePage(body_text="这是正常页面")

        result = check_page(page)  # type: ignore[arg-type]

        self.assertFalse(result.is_illegal)
        self.assertEqual(result.page_type, NORMAL_PAGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.site_init.initialize_site import (
    DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
    DEFAULT_LOGIN_TIMEOUT_SECONDS,
    LOADING_OVERLAY_SELECTOR,
    SUCCESS_CONTENT_SELECTOR,
    SUCCESS_HEADER_SELECTOR,
    SUCCESS_LOGGED_IN_SELECTOR,
    TARGET_HOME_URL,
    has_reached_logged_in_state,
    normalize_url,
)


class FakeLocator:
    def __init__(self, exists: bool, visible: bool) -> None:
        self._exists = exists
        self._visible = visible
        self.first = self

    def count(self) -> int:
        return 1 if self._exists else 0

    def is_visible(self) -> bool:
        return self._visible


class FakePage:
    def __init__(
        self,
        url: str,
        existing_selectors: set[str] | None = None,
        visible_selectors: set[str] | None = None,
    ) -> None:
        self.url = url
        self.existing_selectors = existing_selectors or set()
        self.visible_selectors = visible_selectors or set()

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(
            exists=selector in self.existing_selectors,
            visible=selector in self.visible_selectors,
        )


class TestInitializeSite(unittest.TestCase):
    def test_normalize_url_trims_whitespace(self) -> None:
        # 验证 URL 标准化函数会去掉首尾空白字符。
        self.assertEqual(normalize_url(f"  {TARGET_HOME_URL}  "), TARGET_HOME_URL)

    def test_has_reached_logged_in_state_returns_true_when_all_signals_match(self) -> None:
        # 验证只有目标地址、已登录头部和主体内容同时满足时，才判定为成功。
        page = FakePage(
            TARGET_HOME_URL,
            existing_selectors={
                SUCCESS_HEADER_SELECTOR,
                SUCCESS_LOGGED_IN_SELECTOR,
                SUCCESS_CONTENT_SELECTOR,
            },
        )
        self.assertTrue(has_reached_logged_in_state(page))

    def test_has_reached_logged_in_state_returns_false_when_only_header_exists(self) -> None:
        # 验证只有头部骨架存在时，不会误判为登录成功。
        page = FakePage(
            TARGET_HOME_URL,
            existing_selectors={SUCCESS_HEADER_SELECTOR},
        )
        self.assertFalse(has_reached_logged_in_state(page))

    def test_has_reached_logged_in_state_returns_false_when_loading_overlay_is_visible(self) -> None:
        # 验证预加载层仍然可见时，不会过早判定成功。
        page = FakePage(
            TARGET_HOME_URL,
            existing_selectors={
                SUCCESS_HEADER_SELECTOR,
                SUCCESS_LOGGED_IN_SELECTOR,
                SUCCESS_CONTENT_SELECTOR,
                LOADING_OVERLAY_SELECTOR,
            },
            visible_selectors={LOADING_OVERLAY_SELECTOR},
        )
        self.assertFalse(has_reached_logged_in_state(page))

    def test_has_reached_logged_in_state_returns_false_when_url_differs(self) -> None:
        # 验证即使结构满足，只要 URL 不一致也不会误判。
        page = FakePage(
            "https://analytics.zhihuiya.com/login",
            existing_selectors={
                SUCCESS_HEADER_SELECTOR,
                SUCCESS_LOGGED_IN_SELECTOR,
                SUCCESS_CONTENT_SELECTOR,
            },
        )
        self.assertFalse(has_reached_logged_in_state(page))

    def test_default_timeout_and_poll_interval_are_expected(self) -> None:
        # 验证人工登录流程使用的默认超时和轮询间隔符合需求。
        self.assertEqual(DEFAULT_LOGIN_TIMEOUT_SECONDS, 600.0)
        self.assertEqual(DEFAULT_LOGIN_POLL_INTERVAL_SECONDS, 3.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

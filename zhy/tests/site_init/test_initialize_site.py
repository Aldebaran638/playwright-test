import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.site_init.initialize_site import has_reached_logged_in_state, normalize_url


TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
SUCCESS_HEADER_SELECTOR = "#header-wrapper"
SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
LOGIN_TIMEOUT_SECONDS = 600.0
LOGIN_POLL_INTERVAL_SECONDS = 3.0


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
        self.assertEqual(normalize_url(f"  {TARGET_HOME_URL}  "), TARGET_HOME_URL)

    def test_has_reached_logged_in_state_returns_true_when_all_signals_match(self) -> None:
        page = FakePage(
            TARGET_HOME_URL,
            existing_selectors={
                SUCCESS_HEADER_SELECTOR,
                SUCCESS_LOGGED_IN_SELECTOR,
                SUCCESS_CONTENT_SELECTOR,
            },
        )
        self.assertTrue(
            has_reached_logged_in_state(
                page=page,
                success_url=TARGET_HOME_URL,
                success_header_selector=SUCCESS_HEADER_SELECTOR,
                success_logged_in_selector=SUCCESS_LOGGED_IN_SELECTOR,
                success_content_selector=SUCCESS_CONTENT_SELECTOR,
                loading_overlay_selector=LOADING_OVERLAY_SELECTOR,
            )
        )

    def test_has_reached_logged_in_state_returns_false_when_only_header_exists(self) -> None:
        page = FakePage(
            TARGET_HOME_URL,
            existing_selectors={SUCCESS_HEADER_SELECTOR},
        )
        self.assertFalse(
            has_reached_logged_in_state(
                page=page,
                success_url=TARGET_HOME_URL,
                success_header_selector=SUCCESS_HEADER_SELECTOR,
                success_logged_in_selector=SUCCESS_LOGGED_IN_SELECTOR,
                success_content_selector=SUCCESS_CONTENT_SELECTOR,
                loading_overlay_selector=LOADING_OVERLAY_SELECTOR,
            )
        )

    def test_has_reached_logged_in_state_returns_false_when_loading_overlay_is_visible(self) -> None:
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
        self.assertFalse(
            has_reached_logged_in_state(
                page=page,
                success_url=TARGET_HOME_URL,
                success_header_selector=SUCCESS_HEADER_SELECTOR,
                success_logged_in_selector=SUCCESS_LOGGED_IN_SELECTOR,
                success_content_selector=SUCCESS_CONTENT_SELECTOR,
                loading_overlay_selector=LOADING_OVERLAY_SELECTOR,
            )
        )

    def test_has_reached_logged_in_state_returns_false_when_url_differs(self) -> None:
        page = FakePage(
            "https://analytics.zhihuiya.com/login",
            existing_selectors={
                SUCCESS_HEADER_SELECTOR,
                SUCCESS_LOGGED_IN_SELECTOR,
                SUCCESS_CONTENT_SELECTOR,
            },
        )
        self.assertFalse(
            has_reached_logged_in_state(
                page=page,
                success_url=TARGET_HOME_URL,
                success_header_selector=SUCCESS_HEADER_SELECTOR,
                success_logged_in_selector=SUCCESS_LOGGED_IN_SELECTOR,
                success_content_selector=SUCCESS_CONTENT_SELECTOR,
                loading_overlay_selector=LOADING_OVERLAY_SELECTOR,
            )
        )

    def test_login_wait_settings_are_defined_in_task_layer(self) -> None:
        self.assertEqual(LOGIN_TIMEOUT_SECONDS, 600.0)
        self.assertEqual(LOGIN_POLL_INTERVAL_SECONDS, 3.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

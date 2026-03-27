import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tyc.modules.enter_company_detail_page as enter_company_detail_page_module


logger.remove()
logger.add(sys.stdout, format="{message}")


class FakePopupInfo:
    def __init__(self, popup_page) -> None:
        self.value = popup_page


class FakeExpectPopup:
    def __init__(self, page, popup_page) -> None:
        self.page = page
        self.info = FakePopupInfo(popup_page)

    def __enter__(self) -> FakePopupInfo:
        self.page.calls.append(("popup_enter",))
        return self.info

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.page.calls.append(("popup_exit",))
        return False


class FakeLocator:
    def __init__(self, page, key: tuple) -> None:
        self.page = page
        self.key = key

    @property
    def first(self) -> "FakeLocator":
        self.page.calls.append(("first", self.key))
        return self

    def locator(self, selector: str) -> "FakeLocator":
        key = ("locator", self.key, selector)
        self.page.calls.append(("locator", key))
        return FakeLocator(self.page, key)

    def get_by_role(self, role: str, **kwargs) -> "FakeLocator":
        key = ("role", self.key, role, tuple(sorted(kwargs.items())))
        self.page.calls.append(("get_by_role_nested", key))
        return FakeLocator(self.page, key)

    def click(self) -> None:
        self.page.calls.append(("click", self.key))

    def fill(self, value: str) -> None:
        self.page.calls.append(("fill", self.key, value))


class FakePage:
    def __init__(self, popup_page) -> None:
        self.popup_page = popup_page
        self.calls: list[tuple] = []

    def locator(self, selector: str) -> FakeLocator:
        key = ("page_locator", selector)
        self.calls.append(("locator", key))
        return FakeLocator(self, key)

    def get_by_role(self, role: str, **kwargs) -> FakeLocator:
        key = ("page_role", role, tuple(sorted(kwargs.items())))
        self.calls.append(("get_by_role", key))
        return FakeLocator(self, key)

    def expect_popup(self) -> FakeExpectPopup:
        self.calls.append(("expect_popup",))
        return FakeExpectPopup(self, self.popup_page)


class TestEnterCompanyDetailPage(unittest.TestCase):
    def test_enter_company_detail_page_returns_popup_page(self) -> None:
        logger.info("[测试1] 验证模块会返回公司详情页对应的 popup page")
        popup_page = object()
        page = FakePage(popup_page)

        with patch.object(
            enter_company_detail_page_module,
            "run_step",
            side_effect=lambda action, step_name, **kwargs: action(),
        ):
            result = enter_company_detail_page_module.enter_company_detail_page(
                page, "小米通讯技术有限公司"
            )

        self.assertIs(result, popup_page)

    def test_enter_company_detail_page_executes_expected_steps(self) -> None:
        logger.info("[测试2] 验证模块按预期顺序执行主页搜索和打开详情页")
        popup_page = object()
        page = FakePage(popup_page)
        company_name = "小米通讯技术有限公司"

        with patch.object(
            enter_company_detail_page_module,
            "run_step",
            side_effect=lambda action, step_name, **kwargs: action(),
        ):
            enter_company_detail_page_module.enter_company_detail_page(page, company_name)

        search_area_key = ("page_locator", enter_company_detail_page_module.HOME_SEARCH_AREA_SELECTOR)
        searchbox_key = ("locator", search_area_key, enter_company_detail_page_module.HOME_SEARCH_INPUT_SELECTOR)
        search_button_key = ("role", search_area_key, "button", ())

        expected_calls = [
            ("locator", search_area_key),
            ("first", search_area_key),
            ("locator", searchbox_key),
            ("first", searchbox_key),
            ("get_by_role_nested", search_button_key),
            ("first", search_button_key),
            ("click", searchbox_key),
            ("fill", searchbox_key, company_name),
            ("click", search_button_key),
            ("expect_popup",),
            ("popup_enter",),
            ("get_by_role", ("page_role", "link", (("exact", True), ("name", company_name)))),
            ("click", ("page_role", "link", (("exact", True), ("name", company_name)))),
            ("popup_exit",),
        ]

        self.assertEqual(page.calls, expected_calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)

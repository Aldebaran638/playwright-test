import sys
import unittest
from pathlib import Path

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.login_state import (
    CHECK_INTERVAL_MS,
    LOGGED_IN,
    LOGGED_OUT,
    UNKNOWN,
    get_login_state,
    wait_until_logged_in,
)


logger.remove()
logger.add(sys.stdout, format="{message}")


class FakeLocator:
    def __init__(self, texts: list[str]) -> None:
        self.texts = texts

    def count(self) -> int:
        return len(self.texts)

    @property
    def first(self):
        return self

    def inner_text(self) -> str:
        return self.texts[0]


class FakePage:
    def __init__(self, states: list[int]) -> None:
        self.states = states
        self.index = 0
        self.wait_calls: list[int] = []

    def locator(self, selector: str) -> FakeLocator:
        current_state = self.states[min(self.index, len(self.states) - 1)]
        if selector == ".tyc-nav-user-dropdown-label.tyc-header-nav-link":
            if current_state == LOGGED_IN:
                return FakeLocator(["198****8888"])
            return FakeLocator([])
        if selector == ".tyc-nav-user-btn":
            if current_state == LOGGED_OUT:
                return FakeLocator(["登录/注册"])
            return FakeLocator([])
        return FakeLocator([])

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_calls.append(timeout_ms)
        if self.index < len(self.states) - 1:
            self.index += 1


class TestLoginState(unittest.TestCase):
    def test_get_login_state_detects_logged_in(self) -> None:
        logger.info("[测试1] 验证 get_login_state() 能识别已登录状态")
        page = FakePage([LOGGED_IN])
        self.assertEqual(get_login_state(page), LOGGED_IN)

    def test_get_login_state_detects_logged_out(self) -> None:
        logger.info("[测试2] 验证 get_login_state() 能识别未登录状态")
        page = FakePage([LOGGED_OUT])
        self.assertEqual(get_login_state(page), LOGGED_OUT)

    def test_get_login_state_returns_unknown_when_no_marker(self) -> None:
        logger.info("[测试3] 验证 get_login_state() 在无标记时返回未知状态")
        page = FakePage([UNKNOWN])
        self.assertEqual(get_login_state(page), UNKNOWN)

    def test_wait_until_logged_in_blocks_until_state_changes(self) -> None:
        logger.info("[测试4] 验证 wait_until_logged_in() 会轮询直到用户完成登录")
        page = FakePage([LOGGED_OUT, UNKNOWN, LOGGED_IN])

        wait_until_logged_in(page)

        self.assertEqual(page.wait_calls, [CHECK_INTERVAL_MS, CHECK_INTERVAL_MS])


if __name__ == "__main__":
    unittest.main(verbosity=2)

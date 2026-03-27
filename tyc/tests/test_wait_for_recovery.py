import sys
import unittest
from pathlib import Path

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.page_guard import PageGuardResult
from tyc.modules.wait_for_recovery import WAIT_INTERVAL_MS, wait_until_page_recovered


logger.remove()
logger.add(sys.stdout, format="{message}")


class FakePage:
    def __init__(self) -> None:
        self.wait_calls: list[int] = []

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_calls.append(timeout_ms)


class TestWaitForRecovery(unittest.TestCase):
    def test_wait_until_page_recovered_blocks_until_page_is_normal(self) -> None:
        logger.info("[测试1] 验证 wait_until_page_recovered() 会阻塞直到页面恢复正常")
        fake_page = FakePage()
        states = [
            PageGuardResult(True, "verification_page", "need verify"),
            PageGuardResult(True, "verification_page", "still verify"),
            PageGuardResult(False, "normal_page", "ok"),
        ]
        index = {"value": 0}

        def fake_check_page(page):
            current = states[index["value"]]
            if index["value"] < len(states) - 1:
                index["value"] += 1
            return current

        wait_until_page_recovered(
            lambda: fake_page,
            check_page_func=fake_check_page,
            wait_interval_ms=WAIT_INTERVAL_MS,
        )

        self.assertEqual(fake_page.wait_calls, [WAIT_INTERVAL_MS, WAIT_INTERVAL_MS])


if __name__ == "__main__":
    unittest.main(verbosity=2)

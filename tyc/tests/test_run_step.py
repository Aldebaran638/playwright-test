import sys
import unittest
from pathlib import Path

from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.page_guard import PageGuardResult
from tyc.modules.run_step import run_step


logger.remove()
logger.add(sys.stdout, format="{message}")


class FakePage:
    def __init__(self) -> None:
        self.wait_calls: list[int] = []

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_calls.append(timeout_ms)


class TestRunStep(unittest.TestCase):
    def test_run_step_returns_action_result_after_random_delay(self) -> None:
        logger.info("[测试1] 验证 run_step() 成功后会返回结果并执行随机等待")
        sleep_calls: list[float] = []

        result = run_step(
            lambda: "ok",
            "成功步骤",
            sleep_func=sleep_calls.append,
            random_func=lambda start, end: 1.25,
        )

        self.assertEqual(result, "ok")
        self.assertEqual(sleep_calls, [1.25])

    def test_run_step_retries_on_timeout_and_then_succeeds(self) -> None:
        logger.info("[测试2] 验证 run_step() 在普通超时后会自动重试")
        attempts = {"count": 0}
        sleep_calls: list[float] = []

        def flaky_action() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise PlaywrightTimeoutError("timeout")
            return "done"

        result = run_step(
            flaky_action,
            "超时后成功的步骤",
            sleep_func=sleep_calls.append,
            random_func=lambda start, end: 0.75,
        )

        self.assertEqual(result, "done")
        self.assertEqual(attempts["count"], 3)
        self.assertEqual(sleep_calls, [0.75])

    def test_run_step_waits_for_recovery_when_illegal_page_detected(self) -> None:
        logger.info("[测试3] 验证 run_step() 失败后检测到非法页时会等待恢复再继续")
        attempts = {"count": 0}
        fake_page = FakePage()
        recovery_calls: list[str] = []
        check_calls = {"count": 0}

        def flaky_action() -> str:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise PlaywrightTimeoutError("timeout")
            return "recovered"

        def fake_check_page(page):
            check_calls["count"] += 1
            if check_calls["count"] == 1:
                return PageGuardResult(True, "verification_page", "need verify")
            return PageGuardResult(False, "normal_page", "ok")

        def fake_recovery(page_getter, *, check_page_func):
            recovery_calls.append("called")

        result = run_step(
            flaky_action,
            "非法页恢复步骤",
            page_getter=lambda: fake_page,
            sleep_func=lambda seconds: None,
            random_func=lambda start, end: 0.5,
            check_page_func=fake_check_page,
            recovery_func=fake_recovery,
        )

        self.assertEqual(result, "recovered")
        self.assertEqual(attempts["count"], 2)
        self.assertEqual(recovery_calls, ["called"])

    def test_run_step_raises_after_max_retries(self) -> None:
        logger.info("[测试4] 验证 run_step() 超过最大重试次数后会抛出异常")
        attempts = {"count": 0}

        def always_timeout() -> None:
            attempts["count"] += 1
            raise PlaywrightTimeoutError("timeout")

        with self.assertRaises(PlaywrightTimeoutError):
            run_step(
                always_timeout,
                "始终超时的步骤",
                sleep_func=lambda seconds: None,
                random_func=lambda start, end: 0.5,
            )

        self.assertEqual(attempts["count"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path

from loguru import logger
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.run_step import StepResult, run_step


logger.remove()
logger.add(sys.stdout, format="{message}")


class TestRunStep(unittest.TestCase):
    def test_run_step_returns_step_result_on_success(self) -> None:
        logger.info("[测试1] 验证 run_step() 成功时会返回 StepResult(ok=True)")

        result = run_step(
            lambda: "ok",
            step_name="成功步骤",
        )

        self.assertIsInstance(result, StepResult)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, "ok")
        self.assertIsNone(result.error)

    def test_run_step_retries_and_then_succeeds(self) -> None:
        logger.info("[测试2] 验证 run_step() 会按 retries 次数进行重试")
        attempts = {"count": 0}

        def flaky_action() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise PlaywrightTimeoutError("timeout")
            return "done"

        result = run_step(
            flaky_action,
            step_name="超时后成功的步骤",
            retries=2,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.value, "done")
        self.assertEqual(attempts["count"], 3)

    def test_run_step_returns_failed_step_result_when_not_critical(self) -> None:
        logger.info("[测试3] 验证非关键步骤失败后会返回 StepResult(ok=False)")

        def always_timeout() -> None:
            raise PlaywrightTimeoutError("timeout")

        result = run_step(
            always_timeout,
            step_name="失败但可跳过的步骤",
            retries=1,
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.value)
        self.assertIsInstance(result.error, PlaywrightTimeoutError)

    def test_run_step_raises_when_critical_step_fails(self) -> None:
        logger.info("[测试4] 验证关键步骤失败后会直接抛出异常")
        attempts = {"count": 0}

        def always_timeout() -> None:
            attempts["count"] += 1
            raise PlaywrightTimeoutError("timeout")

        with self.assertRaises(PlaywrightTimeoutError):
            run_step(
                always_timeout,
                step_name="关键失败步骤",
                critical=True,
                retries=3,
            )

        self.assertEqual(attempts["count"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

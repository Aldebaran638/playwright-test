import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.common.run_step import StepResult, run_step_async


class TestRunStepAsync(unittest.IsolatedAsyncioTestCase):
    # 测试成功情况下，run_step_async 是否能正确返回成功结果
    async def test_returns_success_result_when_step_succeeds(self) -> None:
        async def successful_step() -> str:
            return "ok"

        result = await run_step_async(successful_step)

        self.assertIsInstance(result, StepResult)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, "ok")
        self.assertIsNone(result.error)
    # 测试非关键步骤失败时，是否返回失败结果而不是抛出异常
    async def test_returns_failed_result_when_non_critical_step_fails(self) -> None:
        async def failing_step() -> str:
            raise ValueError("step failed")

        result = await run_step_async(failing_step, critical=False)

        self.assertIsInstance(result, StepResult)
        self.assertFalse(result.ok)
        self.assertIsNone(result.value)
        self.assertIsInstance(result.error, ValueError)
        self.assertEqual(str(result.error), "step failed")
    # 测试关键步骤失败时，是否会向外抛出原始异常
    async def test_raises_error_when_critical_step_fails(self) -> None:
        async def failing_step() -> str:
            raise ValueError("step failed")

        with self.assertRaises(ValueError) as context:
            await run_step_async(failing_step, critical=True)

        self.assertEqual(str(context.exception), "step failed")
    # 测试失败后是否会按照设定次数重试，并在后续成功时返回成功结果
    async def test_retries_and_succeeds_on_second_attempt(self) -> None:
        call_count = 0

        async def flaky_step() -> str:
            # nonlocal,这一句话使用了这个关键词,就代表这里的call_count是外层函数的call_count,而不是flaky_step函数内部的一个局部变量.
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise ValueError("temporary failure")

            return "ok after retry"

        result = await run_step_async(flaky_step, retries=1, critical=False)

        self.assertIsInstance(result, StepResult)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, "ok after retry")
        self.assertIsNone(result.error)
        self.assertEqual(call_count, 2)

    # 测试重试次数耗尽后，非关键步骤是否返回失败结果
    async def test_returns_failed_result_after_all_retries_for_non_critical_step(self) -> None:
        call_count = 0

        async def always_failing_step() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("step failed after retries")

        result = await run_step_async(always_failing_step, retries=2, critical=False)

        self.assertIsInstance(result, StepResult)
        self.assertFalse(result.ok)
        self.assertIsNone(result.value)
        self.assertIsInstance(result.error, ValueError)
        self.assertEqual(str(result.error), "step failed after retries")
        self.assertEqual(call_count, 3)

    # 测试重试次数耗尽后，关键步骤是否会向外抛出异常
    async def test_raises_error_after_all_retries_for_critical_step(self) -> None:
        call_count = 0

        async def always_failing_step() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("step failed after retries")

        with self.assertRaises(ValueError) as context:
            await run_step_async(always_failing_step, retries=2, critical=True)

        self.assertEqual(str(context.exception), "step failed after retries")
        self.assertEqual(call_count, 3)
if __name__ == "__main__":
    unittest.main(verbosity=2)

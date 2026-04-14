import unittest

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

if __name__ == "__main__":
    unittest.main()
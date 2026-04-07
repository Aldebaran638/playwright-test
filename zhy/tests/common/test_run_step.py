import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.common.run_step import run_step_async


class TestRunStepAsync(unittest.IsolatedAsyncioTestCase):
    async def test_run_step_async_returns_value_on_success(self) -> None:
        async def succeed() -> str:
            return "ok"

        result = await run_step_async(succeed, step_name="success")
        self.assertTrue(result.ok)
        self.assertEqual(result.value, "ok")
        self.assertIsNone(result.error)

    async def test_run_step_async_returns_error_on_non_critical_failure(self) -> None:
        async def fail() -> str:
            raise ValueError("boom")

        result = await run_step_async(fail, step_name="failure", critical=False)
        self.assertFalse(result.ok)
        self.assertIsNone(result.value)
        self.assertIsInstance(result.error, ValueError)

    async def test_run_step_async_raises_on_critical_failure(self) -> None:
        async def fail() -> str:
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            await run_step_async(fail, step_name="critical_failure", critical=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

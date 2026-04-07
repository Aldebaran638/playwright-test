import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.browser_context.browser_context_workflow import (
    BrowserContextProbeResult,
    BrowserContextUserInput,
    get_next_mode,
    infer_requested_mode,
    path_exists,
    resolve_browser_context_mode,
)


class TestBrowserContextWorkflow(unittest.TestCase):
    def test_infer_requested_mode_covers_four_cases(self) -> None:
        # 验证首选模式推断覆盖四种输入组合。
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput("C:/Edge/msedge.exe", "D:/data")),
            "full_persistent",
        )
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput("C:/Edge/msedge.exe", None)),
            "custom_browser_ephemeral",
        )
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput(None, "D:/data")),
            "default_browser_persistent",
        )
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput(None, None)),
            "default_browser_ephemeral",
        )

    def test_get_next_mode_uses_expected_downgrade_rules(self) -> None:
        # 验证不同失败原因会映射到预期的下一档模式。
        self.assertEqual(get_next_mode("full_persistent", "browser_unavailable"), "default_browser_persistent")
        self.assertEqual(get_next_mode("full_persistent", "user_data_unavailable"), "custom_browser_ephemeral")
        self.assertEqual(get_next_mode("custom_browser_ephemeral", "browser_unavailable"), "default_browser_ephemeral")
        self.assertIsNone(get_next_mode("default_browser_ephemeral", "startup_failed"))

    def test_resolve_browser_context_mode_returns_success_after_fallback(self) -> None:
        # 验证首选模式失败后，工作流会继续降级并返回成功结果。
        user_input = BrowserContextUserInput("C:/bad/msedge.exe", "D:/data")

        def fake_probe(mode: str, normalized_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            if mode == "full_persistent":
                return BrowserContextProbeResult(
                    mode=mode,
                    success=False,
                    failure_reason="browser_unavailable",
                    detail="browser path invalid",
                )
            return BrowserContextProbeResult(
                mode=mode,
                success=True,
                detail="fallback works",
            )

        result = resolve_browser_context_mode(user_input, fake_probe)

        self.assertTrue(result.success)
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.resolved_mode, "default_browser_persistent")

    def test_path_exists_handles_existing_and_missing_paths(self) -> None:
        # 验证路径判断函数能区分存在、缺失和空值。
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.assertTrue(path_exists(tmp_dir))

        self.assertFalse(path_exists("Z:/definitely_missing_path"))
        self.assertFalse(path_exists(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)

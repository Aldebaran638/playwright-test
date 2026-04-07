import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.browser_context.browser_context_probe import probe_browser_context_mode
from zhy.modules.browser_context.browser_context_workflow import BrowserContextUserInput


class TestBrowserContextProbe(unittest.TestCase):
    def test_full_persistent_returns_browser_unavailable_when_browser_is_missing(self) -> None:
        # 验证第一档模式下仅浏览器缺失时，会返回 browser_unavailable。
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = probe_browser_context_mode(
                "full_persistent",
                BrowserContextUserInput(
                    browser_executable_path="Z:/missing_browser.exe",
                    user_data_dir=tmp_dir,
                ),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, "browser_unavailable")

    def test_default_browser_ephemeral_always_succeeds(self) -> None:
        # 验证第四档兜底模式默认成功。
        result = probe_browser_context_mode(
            "default_browser_ephemeral",
            BrowserContextUserInput(),
        )

        self.assertTrue(result.success)
        self.assertIsNone(result.failure_reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)

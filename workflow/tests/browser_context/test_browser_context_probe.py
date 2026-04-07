import sys
import tempfile
import unittest
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.modules.browser_context.browser_context_probe import probe_browser_context_mode
from workflow.modules.browser_context.browser_context_workflow import BrowserContextUserInput


logger.remove()
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}")


class TestBrowserContextProbe(unittest.TestCase):
    def test_full_persistent_returns_browser_unavailable_when_only_browser_is_missing(self) -> None:
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

    def test_full_persistent_returns_user_data_unavailable_when_only_user_data_is_missing(self) -> None:
        # 验证第一档模式下仅用户数据目录缺失时，会返回 user_data_unavailable。
        with tempfile.NamedTemporaryFile() as tmp_file:
            result = probe_browser_context_mode(
                "full_persistent",
                BrowserContextUserInput(
                    browser_executable_path=tmp_file.name,
                    user_data_dir="Z:/missing_user_data",
                ),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, "user_data_unavailable")

    def test_custom_browser_ephemeral_succeeds_when_browser_exists(self) -> None:
        # 验证第二档模式在浏览器路径存在时直接成功。
        with tempfile.NamedTemporaryFile() as tmp_file:
            result = probe_browser_context_mode(
                "custom_browser_ephemeral",
                BrowserContextUserInput(browser_executable_path=tmp_file.name),
            )

        self.assertTrue(result.success)
        self.assertIsNone(result.failure_reason)

    def test_default_browser_persistent_returns_user_data_unavailable_when_data_is_missing(self) -> None:
        # 验证第三档模式在用户数据目录缺失时继续降级。
        result = probe_browser_context_mode(
            "default_browser_persistent",
            BrowserContextUserInput(user_data_dir="Z:/missing_user_data"),
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, "user_data_unavailable")

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

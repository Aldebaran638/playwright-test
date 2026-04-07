import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.modules.browser_context.browser_context_cli import collect_browser_context_user_input
from workflow.modules.common.runtime_config import WorkflowRuntimeConfig, set_runtime_config


class TestBrowserContextCli(unittest.TestCase):
    def setUp(self) -> None:
        set_runtime_config(WorkflowRuntimeConfig(debug_mode=False))

    def test_collect_browser_context_user_input_supports_skip_and_trim(self) -> None:
        # 验证终端输入支持自动去空格，并允许第二个输入直接跳过。
        with patch("builtins.input", side_effect=["  C:/Edge/msedge.exe  ", "   "]):
            result = collect_browser_context_user_input()

        self.assertEqual(result.browser_executable_path, "C:/Edge/msedge.exe")
        self.assertIsNone(result.user_data_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.modules.browser_context.browser_context_cli import collect_browser_context_user_input
from workflow.modules.browser_context.browser_context_workflow import BrowserContextUserInput
from workflow.modules.common.runtime_config import WorkflowRuntimeConfig, set_runtime_config


class TestBrowserContextCli(unittest.TestCase):
    def setUp(self) -> None:
        set_runtime_config(WorkflowRuntimeConfig(debug_mode=False))

    def test_collect_browser_context_user_input_uses_config_mode_when_selected(self) -> None:
        # 验证用户选择配置模式时，会直接返回配置文件中的输入。
        result = collect_browser_context_user_input(
            mode_selector=lambda config_available, timeout_seconds: "config",
            config_loader=lambda config_path: BrowserContextUserInput(
                browser_executable_path=" C:/Edge/msedge.exe ",
                user_data_dir=" D:/browser_data ",
            ),
        )

        self.assertEqual(result.browser_executable_path, "C:/Edge/msedge.exe")
        self.assertEqual(result.user_data_dir, "D:/browser_data")

    def test_collect_browser_context_user_input_falls_back_to_manual_when_config_is_empty(self) -> None:
        # 验证配置为空时，即使超时或选择配置，也会继续进入手动模式。
        prompts = iter(["  C:/Chrome/chrome.exe ", "   "])
        result = collect_browser_context_user_input(
            mode_selector=lambda config_available, timeout_seconds: None,
            config_loader=lambda config_path: BrowserContextUserInput(),
            prompt_optional_path=lambda prompt: next(prompts).strip() or None,
        )

        self.assertEqual(result.browser_executable_path, "C:/Chrome/chrome.exe")
        self.assertIsNone(result.user_data_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)

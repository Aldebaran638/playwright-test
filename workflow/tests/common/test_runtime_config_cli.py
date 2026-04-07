import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.modules.common.runtime_config import (
    WorkflowRuntimeConfig,
    get_runtime_config,
    is_debug_mode,
    set_runtime_config,
)
from workflow.modules.common.runtime_config_cli import collect_runtime_config


class TestRuntimeConfigCli(unittest.TestCase):
    def setUp(self) -> None:
        set_runtime_config(WorkflowRuntimeConfig(debug_mode=False))

    def test_collect_runtime_config_can_enable_debug_mode(self) -> None:
        # 验证用户输入 y 时，会正确开启调试模式。
        with patch("builtins.input", side_effect=["y"]):
            result = collect_runtime_config()

        self.assertTrue(result.debug_mode)
        self.assertTrue(is_debug_mode())
        self.assertTrue(get_runtime_config().debug_mode)

    def test_collect_runtime_config_uses_default_false_when_skipped(self) -> None:
        # 验证用户直接回车时，会使用默认的关闭状态。
        with patch("builtins.input", side_effect=[""]):
            result = collect_runtime_config()

        self.assertFalse(result.debug_mode)
        self.assertFalse(is_debug_mode())


if __name__ == "__main__":
    unittest.main(verbosity=2)

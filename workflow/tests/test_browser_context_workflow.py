import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.modules.browser_context_workflow import (
    BrowserContextProbeResult,
    BrowserContextUserInput,
    build_terminal_message,
    get_next_mode,
    infer_requested_mode,
    path_exists,
    resolve_browser_context_mode,
)


logger.remove()
logger.add(
    sys.stdout,
    format="{time:HH:mm:ss} | {level} | {message}",
)


ProbeFunc = Callable[[str, BrowserContextUserInput], BrowserContextProbeResult]


class TestBrowserContextWorkflow(unittest.TestCase):
    @staticmethod
    def _log_probe_result(mode: str, result: BrowserContextProbeResult) -> BrowserContextProbeResult:
        logger.info(
            "[探测] mode={} success={} failure_reason={} detail={}",
            mode,
            result.success,
            result.failure_reason,
            result.detail,
        )
        return result

    def test_user_input_normalized_trims_whitespace(self) -> None:
        logger.info("[测试1] 验证用户输入归一化会清理空格并把空字符串转成 None")
        user_input = BrowserContextUserInput(
            browser_executable_path="  C:/Edge/msedge.exe  ",
            user_data_dir="   ",
        )

        normalized = user_input.normalized()

        self.assertEqual(normalized.browser_executable_path, "C:/Edge/msedge.exe")
        self.assertIsNone(normalized.user_data_dir)

    def test_infer_requested_mode_covers_all_four_cases(self) -> None:
        logger.info("[测试2] 验证目标模式推断覆盖四种输入情况")
        self.assertEqual(
            infer_requested_mode(
                BrowserContextUserInput("C:/Edge/msedge.exe", "D:/browser_data")
            ),
            "full_persistent",
        )
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput("C:/Edge/msedge.exe", None)),
            "custom_browser_ephemeral",
        )
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput(None, "D:/browser_data")),
            "default_browser_persistent",
        )
        self.assertEqual(
            infer_requested_mode(BrowserContextUserInput(None, None)),
            "default_browser_ephemeral",
        )

    def test_get_next_mode_follows_expected_downgrade_rules(self) -> None:
        logger.info("[测试3] 验证不同失败原因会触发正确的降级目标")
        self.assertEqual(
            get_next_mode("full_persistent", "browser_unavailable"),
            "default_browser_persistent",
        )
        self.assertEqual(
            get_next_mode("full_persistent", "user_data_unavailable"),
            "custom_browser_ephemeral",
        )
        self.assertEqual(
            get_next_mode("full_persistent", "user_data_incompatible"),
            "custom_browser_ephemeral",
        )
        self.assertEqual(
            get_next_mode("full_persistent", "startup_failed"),
            "default_browser_ephemeral",
        )
        self.assertEqual(
            get_next_mode("custom_browser_ephemeral", "browser_unavailable"),
            "default_browser_ephemeral",
        )
        self.assertEqual(
            get_next_mode("default_browser_persistent", "user_data_incompatible"),
            "default_browser_ephemeral",
        )
        self.assertIsNone(get_next_mode("default_browser_ephemeral", "startup_failed"))

    def test_resolve_browser_context_mode_succeeds_without_fallback(self) -> None:
        logger.info("[测试4] 验证主流程在首次兼容测试成功时直接返回")
        user_input = BrowserContextUserInput("C:/Edge/msedge.exe", "D:/browser_data")
        probe_calls: list[str] = []

        def fake_probe(mode: str, normalized_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            probe_calls.append(mode)
            return self._log_probe_result(
                mode,
                BrowserContextProbeResult(
                    mode=mode,
                    success=True,
                    detail="full persistent startup ok",
                ),
            )

        result = resolve_browser_context_mode(user_input, fake_probe)

        self.assertTrue(result.success)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.requested_mode, "full_persistent")
        self.assertEqual(result.resolved_mode, "full_persistent")
        self.assertEqual(result.fallback_chain, ["full_persistent"])
        self.assertEqual(probe_calls, ["full_persistent"])

    def test_resolve_browser_context_mode_downgrades_when_browser_is_unavailable(self) -> None:
        logger.info("[测试5] 验证浏览器不可用时会从第一档降级到第三档")
        user_input = BrowserContextUserInput("C:/bad/msedge.exe", "D:/browser_data")
        probe_calls: list[str] = []

        def fake_probe(mode: str, normalized_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            probe_calls.append(mode)
            if mode == "full_persistent":
                return self._log_probe_result(
                    mode,
                    BrowserContextProbeResult(
                        mode=mode,
                        success=False,
                        failure_reason="browser_unavailable",
                        detail="browser path is invalid",
                    ),
                )
            if mode == "default_browser_persistent":
                return self._log_probe_result(
                    mode,
                    BrowserContextProbeResult(
                        mode=mode,
                        success=True,
                        detail="default chromium + user data startup ok",
                    ),
                )
            raise AssertionError(f"unexpected mode: {mode}")

        result = resolve_browser_context_mode(user_input, fake_probe)

        self.assertTrue(result.success)
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.requested_mode, "full_persistent")
        self.assertEqual(result.resolved_mode, "default_browser_persistent")
        self.assertEqual(
            result.fallback_chain,
            ["full_persistent", "default_browser_persistent"],
        )
        self.assertEqual(
            probe_calls,
            ["full_persistent", "default_browser_persistent"],
        )

    def test_resolve_browser_context_mode_downgrades_when_user_data_is_unavailable(self) -> None:
        logger.info("[测试6] 验证数据目录不可用时会从第一档降级到第二档")
        user_input = BrowserContextUserInput("C:/Edge/msedge.exe", "D:/broken_data")

        def fake_probe(mode: str, normalized_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            if mode == "full_persistent":
                return self._log_probe_result(
                    mode,
                    BrowserContextProbeResult(
                        mode=mode,
                        success=False,
                        failure_reason="user_data_unavailable",
                        detail="user data dir is missing",
                    ),
                )
            if mode == "custom_browser_ephemeral":
                return self._log_probe_result(
                    mode,
                    BrowserContextProbeResult(
                        mode=mode,
                        success=True,
                        detail="custom browser without user data startup ok",
                    ),
                )
            raise AssertionError(f"unexpected mode: {mode}")

        result = resolve_browser_context_mode(user_input, fake_probe)

        self.assertTrue(result.success)
        self.assertEqual(result.requested_mode, "full_persistent")
        self.assertEqual(result.resolved_mode, "custom_browser_ephemeral")
        self.assertEqual(
            result.fallback_chain,
            ["full_persistent", "custom_browser_ephemeral"],
        )

    def test_resolve_browser_context_mode_downgrades_to_default_ephemeral_when_user_data_is_incompatible(self) -> None:
        logger.info("[测试7] 验证仅提供数据目录且不兼容时，会降级到第四档")
        user_input = BrowserContextUserInput(None, "D:/sogou_copy")

        def fake_probe(mode: str, normalized_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            if mode == "default_browser_persistent":
                return self._log_probe_result(
                    mode,
                    BrowserContextProbeResult(
                        mode=mode,
                        success=False,
                        failure_reason="user_data_incompatible",
                        detail="user data dir is incompatible with default chromium",
                    ),
                )
            if mode == "default_browser_ephemeral":
                return self._log_probe_result(
                    mode,
                    BrowserContextProbeResult(
                        mode=mode,
                        success=True,
                        detail="default chromium ephemeral startup ok",
                    ),
                )
            raise AssertionError(f"unexpected mode: {mode}")

        result = resolve_browser_context_mode(user_input, fake_probe)

        self.assertTrue(result.success)
        self.assertEqual(result.requested_mode, "default_browser_persistent")
        self.assertEqual(result.resolved_mode, "default_browser_ephemeral")
        self.assertEqual(
            result.fallback_chain,
            ["default_browser_persistent", "default_browser_ephemeral"],
        )

    def test_resolve_browser_context_mode_returns_failure_when_all_modes_fail(self) -> None:
        logger.info("[测试8] 验证所有模式都失败时，主流程会返回最终失败结果")
        user_input = BrowserContextUserInput("C:/bad/msedge.exe", None)

        def fake_probe(mode: str, normalized_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            return self._log_probe_result(
                mode,
                BrowserContextProbeResult(
                    mode=mode,
                    success=False,
                    failure_reason="browser_unavailable"
                    if mode == "custom_browser_ephemeral"
                    else "startup_failed",
                    detail=f"{mode} failed",
                ),
            )

        result = resolve_browser_context_mode(user_input, fake_probe)

        self.assertFalse(result.success)
        self.assertIsNone(result.resolved_mode)
        self.assertTrue(result.used_fallback)
        self.assertEqual(
            result.fallback_chain,
            ["custom_browser_ephemeral", "default_browser_ephemeral"],
        )
        self.assertEqual(result.reason, "all browser context modes failed")

    def test_build_terminal_message_returns_non_empty_text(self) -> None:
        logger.info("[测试9] 验证各模式都有对应的终端提示文案")
        for mode in (
            "full_persistent",
            "custom_browser_ephemeral",
            "default_browser_persistent",
            "default_browser_ephemeral",
        ):
            self.assertTrue(build_terminal_message(mode))

    def test_path_exists_handles_existing_and_missing_path(self) -> None:
        logger.info("[测试10] 验证路径辅助函数能区分存在和不存在的路径")
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.assertTrue(path_exists(tmp_dir))

        self.assertFalse(path_exists("Z:/definitely_missing_path_for_test"))
        self.assertFalse(path_exists(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from loguru import logger


BrowserEnvMode = Literal[
    "full_persistent",
    "custom_browser_ephemeral",
    "default_browser_persistent",
    "default_browser_ephemeral",
]

FailureReason = Literal[
    "browser_unavailable",
    "user_data_unavailable",
    "user_data_incompatible",
    "startup_failed",
]


@dataclass(frozen=True)
class BrowserContextUserInput:
    browser_executable_path: str | None = None
    user_data_dir: str | None = None

    def normalized(self) -> "BrowserContextUserInput":
        # 统一清理空白输入，避免后续把空字符串误判成有效路径。
        browser_path = (self.browser_executable_path or "").strip() or None
        user_data_dir = (self.user_data_dir or "").strip() or None
        return BrowserContextUserInput(
            browser_executable_path=browser_path,
            user_data_dir=user_data_dir,
        )


@dataclass(frozen=True)
class BrowserContextProbeResult:
    mode: BrowserEnvMode
    success: bool
    failure_reason: FailureReason | None = None
    detail: str = ""


@dataclass
class BrowserContextWorkflowResult:
    requested_mode: BrowserEnvMode
    resolved_mode: BrowserEnvMode | None
    success: bool
    used_fallback: bool
    fallback_chain: list[BrowserEnvMode] = field(default_factory=list)
    reason: str = ""
    messages: list[str] = field(default_factory=list)


def infer_requested_mode(user_input: BrowserContextUserInput) -> BrowserEnvMode:
    # 根据用户提供的两类路径输入，推断首选浏览器上下文模式。
    normalized = user_input.normalized()
    logger.debug("[core] infer requested mode from normalized input: {}", normalized)

    if normalized.browser_executable_path and normalized.user_data_dir:
        return "full_persistent"
    if normalized.browser_executable_path:
        return "custom_browser_ephemeral"
    if normalized.user_data_dir:
        return "default_browser_persistent"
    return "default_browser_ephemeral"


def get_next_mode(
    current_mode: BrowserEnvMode,
    failure_reason: FailureReason | None,
) -> BrowserEnvMode | None:
    # 根据失败原因计算降级后的下一档模式。
    logger.debug(
        "[core] calculate next mode: current_mode={} failure_reason={}",
        current_mode,
        failure_reason,
    )
    if current_mode == "full_persistent":
        if failure_reason == "browser_unavailable":
            return "default_browser_persistent"
        if failure_reason in {"user_data_unavailable", "user_data_incompatible"}:
            return "custom_browser_ephemeral"
        return "default_browser_ephemeral"

    if current_mode in {"custom_browser_ephemeral", "default_browser_persistent"}:
        return "default_browser_ephemeral"

    return None


def build_terminal_message(mode: BrowserEnvMode) -> str:
    # 为当前尝试模式生成统一的终端提示文案。
    if mode == "full_persistent":
        return "Current attempt mode: custom browser + user data dir (persistent)"
    if mode == "custom_browser_ephemeral":
        return "Current attempt mode: custom browser + temporary context"
    if mode == "default_browser_persistent":
        return "Current attempt mode: default Chromium + user data dir (persistent)"
    return "Current attempt mode: default Chromium + temporary context"


def resolve_browser_context_mode(
    user_input: BrowserContextUserInput,
    probe: Callable[[BrowserEnvMode, BrowserContextUserInput], BrowserContextProbeResult],
) -> BrowserContextWorkflowResult:
    # 串联首选模式推断、兼容探测和降级流程，输出最终的结构化结果。
    normalized = user_input.normalized()
    requested_mode = infer_requested_mode(normalized)
    logger.info("[core] requested mode resolved: {}", requested_mode)
    current_mode: BrowserEnvMode | None = requested_mode
    fallback_chain: list[BrowserEnvMode] = []
    messages: list[str] = []

    while current_mode is not None:
        # 每次循环都尝试当前模式，并在失败时决定是否继续降级。
        fallback_chain.append(current_mode)
        messages.append(build_terminal_message(current_mode))

        probe_result = probe(current_mode, normalized)
        logger.debug("[core] probe result: {}", probe_result)
        if probe_result.success:
            if current_mode == requested_mode:
                messages.append(f"Compatibility probe passed. Final mode: {current_mode}")
            else:
                messages.append(f"Fallback probe passed. Final mode: {current_mode}")

            return BrowserContextWorkflowResult(
                requested_mode=requested_mode,
                resolved_mode=current_mode,
                success=True,
                used_fallback=current_mode != requested_mode,
                fallback_chain=fallback_chain,
                reason=probe_result.detail,
                messages=messages,
            )

        failure_reason = probe_result.failure_reason or "startup_failed"
        detail = probe_result.detail or failure_reason
        messages.append(f"Mode {current_mode} failed compatibility probe: {detail}")
        logger.info("[core] mode {} failed: {}", current_mode, detail)

        next_mode = get_next_mode(current_mode, failure_reason)
        if next_mode is not None:
            messages.append(f"Downgrade to next mode: {next_mode}")
            logger.info("[core] downgrade to {}", next_mode)
        current_mode = next_mode

    # 如果所有模式都失败，返回统一的失败结果给上层处理。
    messages.append("All browser context modes failed.")
    logger.warning("[core] all browser context modes failed")
    return BrowserContextWorkflowResult(
        requested_mode=requested_mode,
        resolved_mode=None,
        success=False,
        used_fallback=len(fallback_chain) > 1,
        fallback_chain=fallback_chain,
        reason="all browser context modes failed",
        messages=messages,
    )


def path_exists(path_value: str | None) -> bool:
    # 统一处理空路径和真实路径存在性判断。
    if not path_value:
        logger.debug("[core] path_exists received empty path")
        return False
    exists = Path(path_value).exists()
    logger.debug("[core] path_exists path={} exists={}", path_value, exists)
    return exists

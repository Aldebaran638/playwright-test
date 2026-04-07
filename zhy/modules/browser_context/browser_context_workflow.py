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

    # 统一清理空白输入，避免把空字符串误判成有效路径。
    def normalized(self) -> "BrowserContextUserInput":
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


# 根据用户输入推断首选浏览器上下文模式。
#
# 参数：
# - user_input: 用户提供的浏览器路径和用户数据目录。
# 返回：
# - 推断出的首选模式。
# 逻辑：
# - 同时提供两种路径时优先走持久化模式，否则按输入完整度逐级降档。
def infer_requested_mode(user_input: BrowserContextUserInput) -> BrowserEnvMode:
    normalized = user_input.normalized()
    logger.debug("[browser_context] 开始推断首选模式，normalized={}", normalized)

    if normalized.browser_executable_path and normalized.user_data_dir:
        return "full_persistent"
    if normalized.browser_executable_path:
        return "custom_browser_ephemeral"
    if normalized.user_data_dir:
        return "default_browser_persistent"
    return "default_browser_ephemeral"


# 根据失败原因计算下一档降级模式。
#
# 参数：
# - current_mode: 当前探测失败的模式。
# - failure_reason: 当前模式失败原因。
# 返回：
# - 下一档要尝试的模式；如果没有下一档则返回 None。
# 逻辑：
# - 第一档会按失败原因决定保留浏览器路径还是保留用户数据目录。
def get_next_mode(
    current_mode: BrowserEnvMode,
    failure_reason: FailureReason | None,
) -> BrowserEnvMode | None:
    logger.debug(
        "[browser_context] 计算降级目标，current_mode={} failure_reason={}",
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


# 为当前尝试模式生成统一终端提示文案。
def build_terminal_message(mode: BrowserEnvMode) -> str:
    if mode == "full_persistent":
        return "当前尝试模式：指定浏览器 + 指定用户数据目录（持久化）"
    if mode == "custom_browser_ephemeral":
        return "当前尝试模式：指定浏览器 + 临时上下文"
    if mode == "default_browser_persistent":
        return "当前尝试模式：默认浏览器 + 指定用户数据目录（持久化）"
    return "当前尝试模式：默认浏览器 + 临时上下文"


# 串联浏览器上下文模式推断、探测和降级流程。
#
# 参数：
# - user_input: 用户提供的浏览器上下文相关输入。
# - probe: 实际执行探测的回调函数。
# 返回：
# - 结构化的浏览器上下文工作流结果。
# 逻辑：
# - 先推断首选模式，再逐档探测；若失败则按规则降级直到成功或全部失败。
def resolve_browser_context_mode(
    user_input: BrowserContextUserInput,
    probe: Callable[[BrowserEnvMode, BrowserContextUserInput], BrowserContextProbeResult],
) -> BrowserContextWorkflowResult:
    normalized = user_input.normalized()
    requested_mode = infer_requested_mode(normalized)
    logger.info("[browser_context] 首选模式已确定：{}", requested_mode)
    current_mode: BrowserEnvMode | None = requested_mode
    fallback_chain: list[BrowserEnvMode] = []
    messages: list[str] = []

    while current_mode is not None:
        # 每次循环都尝试当前模式，失败时再决定是否继续降级。
        fallback_chain.append(current_mode)
        messages.append(build_terminal_message(current_mode))

        probe_result = probe(current_mode, normalized)
        logger.debug("[browser_context] 收到探测结果：{}", probe_result)
        if probe_result.success:
            if current_mode == requested_mode:
                messages.append(f"兼容性探测通过，最终模式：{current_mode}")
            else:
                messages.append(f"降级后的兼容性探测通过，最终模式：{current_mode}")

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
        messages.append(f"模式 {current_mode} 探测失败：{detail}")
        logger.info("[browser_context] 模式 {} 失败：{}", current_mode, detail)

        next_mode = get_next_mode(current_mode, failure_reason)
        if next_mode is not None:
            messages.append(f"开始降级到：{next_mode}")
            logger.info("[browser_context] 准备降级到 {}", next_mode)
        current_mode = next_mode

    # 所有模式都失败时，返回统一失败结果给上层处理。
    messages.append("所有浏览器上下文模式均探测失败。")
    logger.warning("[browser_context] 所有浏览器上下文模式均探测失败")
    return BrowserContextWorkflowResult(
        requested_mode=requested_mode,
        resolved_mode=None,
        success=False,
        used_fallback=len(fallback_chain) > 1,
        fallback_chain=fallback_chain,
        reason="all browser context modes failed",
        messages=messages,
    )


# 判断给定路径是否真实存在。
def path_exists(path_value: str | None) -> bool:
    if not path_value:
        logger.debug("[browser_context] path_exists 收到空路径")
        return False
    exists = Path(path_value).exists()
    logger.debug("[browser_context] path={} exists={}", path_value, exists)
    return exists

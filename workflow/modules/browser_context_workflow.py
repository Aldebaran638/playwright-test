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
        # 统一清理空字符串，避免后续判断时把空白当成有效输入。
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
    normalized = user_input.normalized()
    logger.debug("[内核] 开始推断目标模式 normalized={}", normalized)

    if normalized.browser_executable_path and normalized.user_data_dir:
        logger.debug("[内核] 命中第一档 full_persistent")
        return "full_persistent"
    if normalized.browser_executable_path:
        logger.debug("[内核] 命中第二档 custom_browser_ephemeral")
        return "custom_browser_ephemeral"
    if normalized.user_data_dir:
        logger.debug("[内核] 命中第三档 default_browser_persistent")
        return "default_browser_persistent"
    logger.debug("[内核] 命中第四档 default_browser_ephemeral")
    return "default_browser_ephemeral"


def get_next_mode(
    current_mode: BrowserEnvMode,
    failure_reason: FailureReason | None,
) -> BrowserEnvMode | None:
    # 根据失败原因决定下一档降级目标。
    logger.debug(
        "[内核] 计算下一档降级目标 current_mode={} failure_reason={}",
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
    # 为当前模式生成简洁统一的终端提示文案。
    if mode == "full_persistent":
        return "当前尝试模式：用户指定浏览器 + 用户数据目录（持久化）"
    if mode == "custom_browser_ephemeral":
        return "当前尝试模式：用户指定浏览器 + 临时上下文"
    if mode == "default_browser_persistent":
        return "当前尝试模式：默认 Chromium + 用户数据目录（持久化）"
    return "当前尝试模式：默认 Chromium + 临时上下文"


def resolve_browser_context_mode(
    user_input: BrowserContextUserInput,
    probe: Callable[[BrowserEnvMode, BrowserContextUserInput], BrowserContextProbeResult],
) -> BrowserContextWorkflowResult:
    # 先推断目标类型，再做真实兼容测试；失败后按规则逐步降级。
    normalized = user_input.normalized()
    requested_mode = infer_requested_mode(normalized)
    logger.info("[内核] 已确定首选模式: {}", requested_mode)
    current_mode: BrowserEnvMode | None = requested_mode
    fallback_chain: list[BrowserEnvMode] = []
    messages: list[str] = []

    while current_mode is not None:
        logger.debug("[内核] 开始尝试模式 {}", current_mode)
        fallback_chain.append(current_mode)
        messages.append(build_terminal_message(current_mode))

        probe_result = probe(current_mode, normalized)
        logger.debug("[内核] 探测返回 {}", probe_result)
        if probe_result.success:
            if current_mode == requested_mode:
                messages.append(f"兼容测试通过，最终采用模式：{current_mode}")
            else:
                messages.append(f"降级后兼容测试通过，最终采用模式：{current_mode}")

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
        messages.append(f"模式 {current_mode} 兼容测试失败：{detail}")
        logger.info("[内核] 模式 {} 失败: {}", current_mode, detail)

        next_mode = get_next_mode(current_mode, failure_reason)
        if next_mode is not None:
            messages.append(f"开始降级到：{next_mode}")
            logger.info("[内核] 开始降级到 {}", next_mode)
        current_mode = next_mode

    messages.append("所有浏览器环境模式均测试失败")
    logger.warning("[内核] 所有浏览器环境模式均测试失败")
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
    if not path_value:
        logger.debug("[内核] path_exists 收到空路径")
        return False
    exists = Path(path_value).exists()
    logger.debug("[内核] path_exists path={} exists={}", path_value, exists)
    return exists

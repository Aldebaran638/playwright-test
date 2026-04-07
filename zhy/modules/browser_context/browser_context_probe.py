from loguru import logger

from zhy.modules.browser_context.browser_context_workflow import (
    BrowserContextProbeResult,
    BrowserContextUserInput,
    BrowserEnvMode,
    path_exists,
)


# 对不同浏览器上下文模式做路径级兼容性探测。
#
# 参数：
# - mode: 当前要探测的模式。
# - user_input: 用户提供的浏览器路径和用户数据目录。
# 返回：
# - 探测结果，包含是否成功、失败原因和说明。
# 逻辑：
# - 按模式检查必需路径是否存在，并给出后续降级所需的失败原因。
def probe_browser_context_mode(
    mode: BrowserEnvMode,
    user_input: BrowserContextUserInput,
) -> BrowserContextProbeResult:
    browser_exists = path_exists(user_input.browser_executable_path)
    user_data_exists = path_exists(user_input.user_data_dir)
    logger.debug(
        "[browser_context_probe] mode={} browser_exists={} user_data_exists={}",
        mode,
        browser_exists,
        user_data_exists,
    )

    if mode == "full_persistent":
        # 第一档同时依赖浏览器路径和用户数据目录。
        if not browser_exists and user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="browser_unavailable",
                detail="指定浏览器路径不可用，将降级到默认浏览器 + 持久化用户数据目录。",
            )
        if browser_exists and not user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="user_data_unavailable",
                detail="用户数据目录不可用，将降级到指定浏览器 + 临时上下文。",
            )
        if not browser_exists and not user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="startup_failed",
                detail="浏览器路径和用户数据目录均不可用，将降级到默认浏览器 + 临时上下文。",
            )
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="指定浏览器路径和用户数据目录均存在。",
        )

    if mode == "custom_browser_ephemeral":
        # 第二档只要求指定浏览器存在。
        if not browser_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="browser_unavailable",
                detail="指定浏览器不可用，将降级到默认浏览器 + 临时上下文。",
            )
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="指定浏览器路径存在。",
        )

    if mode == "default_browser_persistent":
        # 第三档改用默认浏览器，但仍要求用户数据目录存在。
        if not user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="user_data_unavailable",
                detail="用户数据目录不可用，将降级到默认浏览器 + 临时上下文。",
            )
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="默认浏览器模式下用户数据目录存在。",
        )

    # 第四档作为最终兜底模式，默认允许通过。
    return BrowserContextProbeResult(
        mode=mode,
        success=True,
        detail="默认浏览器 + 临时上下文作为最终兜底模式可继续执行。",
    )

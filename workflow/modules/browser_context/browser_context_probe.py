from loguru import logger

from workflow.modules.browser_context.browser_context_workflow import (
    BrowserContextProbeResult,
    BrowserContextUserInput,
    BrowserEnvMode,
    path_exists,
)


def probe_browser_context_mode(
    mode: BrowserEnvMode,
    user_input: BrowserContextUserInput,
) -> BrowserContextProbeResult:
    # 按不同模式做最基础的路径级探测，决定当前模式是否可继续使用。
    browser_exists = path_exists(user_input.browser_executable_path)
    user_data_exists = path_exists(user_input.user_data_dir)
    logger.debug(
        "[probe] mode={} browser_exists={} user_data_exists={}",
        mode,
        browser_exists,
        user_data_exists,
    )

    if mode == "full_persistent":
        # 第一档同时依赖浏览器路径和用户数据目录，缺任何一个都要降级。
        if not browser_exists and user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="browser_unavailable",
                detail="Browser path is unavailable. Downgrade to default browser + persistent user data.",
            )
        if browser_exists and not user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="user_data_unavailable",
                detail="User data dir is unavailable. Downgrade to custom browser + temporary context.",
            )
        if not browser_exists and not user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="startup_failed",
                detail="Browser path and user data dir are both unavailable. Downgrade to default browser + temporary context.",
            )
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="Path-level probe passed: browser path and user data dir both exist.",
        )

    if mode == "custom_browser_ephemeral":
        # 第二档只要求指定浏览器存在，不再要求用户数据目录。
        if not browser_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="browser_unavailable",
                detail="Custom browser is unavailable. Downgrade to default browser + temporary context.",
            )
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="Path-level probe passed: custom browser exists.",
        )

    if mode == "default_browser_persistent":
        # 第三档改用默认浏览器，但仍然要求用户数据目录存在。
        if not user_data_exists:
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="user_data_unavailable",
                detail="User data dir is unavailable. Downgrade to default browser + temporary context.",
            )
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="Path-level probe passed: user data dir exists for default browser mode.",
        )

    # 第四档作为最后兜底模式，默认允许通过。
    return BrowserContextProbeResult(
        mode=mode,
        success=True,
        detail="Path-level probe passed: default browser + temporary context is the final fallback.",
    )

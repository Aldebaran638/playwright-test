from loguru import logger

from workflow.modules.browser_context_workflow import (
    BrowserContextProbeResult,
    BrowserContextUserInput,
    BrowserEnvMode,
    path_exists,
)


def probe_browser_context_mode(
    mode: BrowserEnvMode,
    user_input: BrowserContextUserInput,
) -> BrowserContextProbeResult:
    """
    浏览器环境工作流的基础探测器。

    当前版本先做路径级探测，让工作流可以完整跑通。
    真正的浏览器启动兼容测试，后续可以在这里继续替换为 Playwright 实现。
    """
    browser_exists = path_exists(user_input.browser_executable_path)
    user_data_exists = path_exists(user_input.user_data_dir)
    logger.debug(
        "[探测] mode={} browser_exists={} user_data_exists={}",
        mode,
        browser_exists,
        user_data_exists,
    )

    if mode == "full_persistent":
        if not browser_exists and user_data_exists:
            logger.info("[探测] 指定浏览器路径无效，准备保留数据目录并降级")
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="browser_unavailable",
                detail="浏览器路径不可用，准备降级到默认浏览器 + 持久化数据目录",
            )
        if browser_exists and not user_data_exists:
            logger.info("[探测] 数据目录无效，准备保留指定浏览器并降级")
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="user_data_unavailable",
                detail="浏览器数据目录不可用，准备降级到指定浏览器 + 临时上下文",
            )
        if not browser_exists and not user_data_exists:
            logger.info("[探测] 浏览器路径和数据目录都无效，准备直接降级到最后兜底模式")
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="startup_failed",
                detail="浏览器路径和数据目录都不可用，准备降级到默认浏览器 + 临时上下文",
            )
        logger.debug("[探测] 第一档路径级探测通过")
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="路径级探测通过：指定浏览器和数据目录都存在",
        )

    if mode == "custom_browser_ephemeral":
        if not browser_exists:
            logger.info("[探测] 指定浏览器路径无效，准备降级到默认浏览器")
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="browser_unavailable",
                detail="指定浏览器不可用，准备降级到默认浏览器 + 临时上下文",
            )
        logger.debug("[探测] 第二档路径级探测通过")
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="路径级探测通过：指定浏览器可用",
        )

    if mode == "default_browser_persistent":
        if not user_data_exists:
            logger.info("[探测] 数据目录无效，准备降级到默认浏览器临时上下文")
            return BrowserContextProbeResult(
                mode=mode,
                success=False,
                failure_reason="user_data_unavailable",
                detail="数据目录不可用，准备降级到默认浏览器 + 临时上下文",
            )
        logger.debug("[探测] 第三档路径级探测通过")
        return BrowserContextProbeResult(
            mode=mode,
            success=True,
            detail="路径级探测通过：默认浏览器模式下数据目录存在",
        )

    logger.debug("[探测] 第四档作为最后兜底默认通过")
    return BrowserContextProbeResult(
        mode=mode,
        success=True,
        detail="路径级探测通过：默认浏览器 + 临时上下文总是可作为最后兜底",
    )

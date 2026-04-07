from dataclasses import dataclass
from typing import Callable

from loguru import logger
from playwright.sync_api import Browser, BrowserContext, Playwright

from workflow.modules.browser_context.browser_context_probe import probe_browser_context_mode
from workflow.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    BrowserEnvMode,
    BrowserContextProbeResult,
    resolve_browser_context_mode,
)


class BrowserContextBuildError(RuntimeError):
    def __init__(self, message: str, workflow_result: BrowserContextWorkflowResult) -> None:
        super().__init__(message)
        self.workflow_result = workflow_result


@dataclass
class ManagedBrowserContext:
    context: BrowserContext
    browser: Browser | None
    workflow_result: BrowserContextWorkflowResult

    def close(self) -> None:
        # 统一关闭 context 和临时 browser，避免调用方区分持久化与临时模式。
        self.context.close()
        if self.browser is not None:
            self.browser.close()


def _launch_context_for_mode(
    playwright: Playwright,
    mode: BrowserEnvMode,
    user_input: BrowserContextUserInput,
    headless: bool,
) -> tuple[BrowserContext, Browser | None]:
    # 根据最终模式真正创建 Playwright BrowserContext。
    chromium = playwright.chromium

    if mode == "full_persistent":
        context = chromium.launch_persistent_context(
            user_data_dir=user_input.user_data_dir or "",
            executable_path=user_input.browser_executable_path,
            headless=headless,
        )
        return context, None

    if mode == "custom_browser_ephemeral":
        browser = chromium.launch(
            executable_path=user_input.browser_executable_path,
            headless=headless,
        )
        return browser.new_context(), browser

    if mode == "default_browser_persistent":
        context = chromium.launch_persistent_context(
            user_data_dir=user_input.user_data_dir or "",
            headless=headless,
        )
        return context, None

    browser = chromium.launch(headless=headless)
    return browser.new_context(), browser


# 基于已解析的输入和降级规则创建一个可复用的浏览器上下文句柄。
# 参数：
# - playwright: 当前 sync_playwright() 提供的 Playwright 对象。
# - user_input: 浏览器路径和用户数据目录输入。
# - headless: 是否以无头模式启动浏览器。
# 返回：
# - 一个统一封装了 context、browser 和工作流结果的句柄对象。
def build_browser_context(
    playwright: Playwright,
    user_input: BrowserContextUserInput,
    probe: Callable[[BrowserEnvMode, BrowserContextUserInput], BrowserContextProbeResult] = probe_browser_context_mode,
    headless: bool = False,
) -> ManagedBrowserContext:
    workflow_result = resolve_browser_context_mode(user_input, probe)
    if not workflow_result.success or workflow_result.resolved_mode is None:
        raise BrowserContextBuildError(
            "Failed to resolve a usable browser context mode.",
            workflow_result,
        )

    normalized = user_input.normalized()
    logger.info("[builder] building browser context with mode={}", workflow_result.resolved_mode)
    context, browser = _launch_context_for_mode(
        playwright,
        workflow_result.resolved_mode,
        normalized,
        headless,
    )
    return ManagedBrowserContext(
        context=context,
        browser=browser,
        workflow_result=workflow_result,
    )

from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Playwright

from zhy.modules.browser_context.browser_context_cli import display_browser_context_workflow_result
from zhy.modules.browser_context.browser_context_probe import probe_browser_context_mode
from zhy.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    BrowserEnvMode,
    resolve_browser_context_mode,
)


@dataclass
class ManagedBrowserContext:
    context: BrowserContext
    browser: Browser | None
    workflow_result: BrowserContextWorkflowResult

    def is_persistent(self) -> bool:
        return self.browser is None

    async def close(self) -> None:
        await self.context.close()
        if self.browser is not None:
            await self.browser.close()


# 简介：按浏览器上下文模式真正启动 Playwright 上下文。
# 参数：
# - playwright: 当前 Playwright 实例。
# - mode: 已解析好的浏览器上下文模式。
# - user_input: 浏览器可执行文件路径和用户数据目录输入。
# - headless: 是否无头启动浏览器。
# 返回值：
# - 返回 (context, browser)，持久化上下文模式下 browser 为 None。
# 逻辑：
# - 根据模式在 persistent context 和普通 browser.new_context() 之间切换。
async def launch_context_for_mode(
    playwright: Playwright,
    mode: BrowserEnvMode,
    user_input: BrowserContextUserInput,
    headless: bool,
) -> tuple[BrowserContext, Browser | None]:
    chromium = playwright.chromium

    if mode == "full_persistent":
        context = await chromium.launch_persistent_context(
            user_data_dir=user_input.user_data_dir or "",
            executable_path=user_input.browser_executable_path,
            headless=headless,
        )
        return context, None

    if mode == "custom_browser_ephemeral":
        browser = await chromium.launch(
            executable_path=user_input.browser_executable_path,
            headless=headless,
        )
        return await browser.new_context(), browser

    if mode == "default_browser_persistent":
        context = await chromium.launch_persistent_context(
            user_data_dir=user_input.user_data_dir or "",
            headless=headless,
        )
        return context, None

    browser = await chromium.launch(headless=headless)
    return await browser.new_context(), browser


# 简介：解析浏览器上下文模式并返回可管理的上下文对象。
# 参数：
# - playwright: 当前 Playwright 实例。
# - user_input: 浏览器路径和用户数据目录输入。
# - headless: 是否无头启动。
# 返回值：
# - ManagedBrowserContext，里面包含 context、browser 和模式解析结果。
# 逻辑：
# - 先用既有 browser_context 工作流解析模式，再按解析结果真正启动上下文。
async def build_browser_context(
    playwright: Playwright,
    user_input: BrowserContextUserInput,
    headless: bool,
) -> ManagedBrowserContext:
    workflow_result = resolve_browser_context_mode(user_input, probe_browser_context_mode)
    display_browser_context_workflow_result(workflow_result)
    if not workflow_result.success or workflow_result.resolved_mode is None:
        raise RuntimeError("failed to resolve a usable browser context mode")

    normalized = user_input.normalized()
    context, browser = await launch_context_for_mode(
        playwright=playwright,
        mode=workflow_result.resolved_mode,
        user_input=normalized,
        headless=headless,
    )
    return ManagedBrowserContext(
        context=context,
        browser=browser,
        workflow_result=workflow_result,
    )
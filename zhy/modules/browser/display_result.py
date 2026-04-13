from loguru import logger

from zhy.modules.browser.context_config import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
)


def _build_section_line(title: str, width: int = 52) -> str:
    return f"{title:-^{width}}"


def _prompt_optional_path(prompt_text: str) -> str | None:
    # 允许用户直接回车跳过当前路径输入。
    user_value = input(prompt_text).strip()
    return user_value or None


# 在终端中收集浏览器上下文初始化所需输入。
def collect_browser_context_user_input() -> BrowserContextUserInput:
    print()
    print(_build_section_line(" 浏览器上下文输入 "))
    print("可选输入 1：浏览器可执行文件路径")
    print("可选输入 2：浏览器用户数据目录")
    print("两项都可以直接回车跳过，系统会自动探测并降级。")
    print()

    logger.info("[browser_context_cli] 开始收集浏览器上下文输入")

    browser_executable_path = _prompt_optional_path(
        "请输入浏览器可执行文件路径（可直接回车跳过）："
    )
    user_data_dir = _prompt_optional_path(
        "请输入浏览器用户数据目录（可直接回车跳过）："
    )

    logger.debug(
        "[browser_context_cli] 收集完成 browser_executable_path={} user_data_dir={}",
        browser_executable_path,
        user_data_dir,
    )
    return BrowserContextUserInput(
        browser_executable_path=browser_executable_path,
        user_data_dir=user_data_dir,
    )


# 把浏览器上下文工作流结果输出成终端可读摘要。
def display_browser_context_workflow_result(
    result: BrowserContextWorkflowResult,
) -> None:
    print()
    print(_build_section_line(" 浏览器上下文结果 "))

    if result.success:
        logger.info("[browser_context_cli] 最终采用模式：{}", result.resolved_mode)
    else:
        logger.warning("[browser_context_cli] 浏览器上下文流程失败")

    if result.used_fallback:
        logger.info("[browser_context_cli] 本次触发了降级流程")

    if result.reason:
        logger.info("[browser_context_cli] 原因：{}", result.reason)

    logger.debug("[browser_context_cli] requested_mode={}", result.requested_mode)
    logger.debug("[browser_context_cli] resolved_mode={}", result.resolved_mode)
    logger.debug("[browser_context_cli] success={}", result.success)
    logger.debug("[browser_context_cli] used_fallback={}", result.used_fallback)
    logger.debug(
        "[browser_context_cli] fallback_chain={}",
        " -> ".join(result.fallback_chain),
    )

    for message in result.messages:
        logger.info("[browser_context_cli] {}", message)

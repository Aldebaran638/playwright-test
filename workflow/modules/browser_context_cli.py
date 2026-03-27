from loguru import logger

from workflow.modules.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
)


def _build_section_line(title: str, width: int = 52) -> str:
    return f"{title:-^{width}}"


def _prompt_optional_path(prompt_text: str) -> str | None:
    """允许用户直接回车跳过某个可选路径输入。"""
    user_value = input(prompt_text).strip()
    return user_value or None


def collect_browser_context_user_input() -> BrowserContextUserInput:
    """在终端里收集浏览器环境模块需要的两个可选路径。"""
    print()
    print(_build_section_line(" Browser Context Input "))
    print("可选输入 1: 浏览器可执行文件路径")
    print("可选输入 2: 浏览器数据文件夹路径")
    print("两项都可以直接回车跳过，工作流会自动选择可用模式。")
    print()

    logger.info("[交互] 开始收集浏览器环境参数")

    browser_executable_path = _prompt_optional_path(
        "请输入浏览器可执行文件路径（可直接回车跳过）: "
    )
    user_data_dir = _prompt_optional_path(
        "请输入浏览器数据文件夹路径（可直接回车跳过）: "
    )

    logger.debug(
        "[交互] 参数收集完成 browser_executable_path={} user_data_dir={}",
        browser_executable_path,
        user_data_dir,
    )
    return BrowserContextUserInput(
        browser_executable_path=browser_executable_path,
        user_data_dir=user_data_dir,
    )


def display_browser_context_workflow_result(
    result: BrowserContextWorkflowResult,
) -> None:
    """把浏览器环境工作流的结构化结果打印成终端可读摘要。"""
    print()
    print(_build_section_line(" Browser Context Result "))

    if result.success:
        logger.info("[结果] 最终采用模式: {}", result.resolved_mode)
    else:
        logger.warning("[结果] 浏览器环境工作流失败")

    if result.used_fallback:
        logger.info("[结果] 本次触发了降级流程")

    if result.reason:
        logger.info("[结果] 原因: {}", result.reason)

    logger.debug("[结果] requested_mode={}", result.requested_mode)
    logger.debug("[结果] resolved_mode={}", result.resolved_mode)
    logger.debug("[结果] success={}", result.success)
    logger.debug("[结果] used_fallback={}", result.used_fallback)
    logger.debug("[结果] fallback_chain={}", " -> ".join(result.fallback_chain))

    for message in result.messages:
        if message.startswith("当前尝试模式："):
            logger.debug("[流程] {}", message)
        else:
            logger.info("[流程] {}", message)

from loguru import logger

from workflow.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
)


def _build_section_line(title: str, width: int = 52) -> str:
    return f"{title:-^{width}}"


def _prompt_optional_path(prompt_text: str) -> str | None:
    # 允许用户直接回车跳过当前路径输入。
    user_value = input(prompt_text).strip()
    return user_value or None


def collect_browser_context_user_input() -> BrowserContextUserInput:
    # 收集浏览器可执行文件路径和用户数据目录，供后续模式探测使用。
    print()
    print(_build_section_line(" Browser Context Input "))
    print("Optional input 1: browser executable path")
    print("Optional input 2: browser user data dir")
    print("Both fields can be skipped. The workflow will probe and downgrade automatically.")
    print()

    logger.info("[cli] collect browser context inputs")

    browser_executable_path = _prompt_optional_path(
        "Browser executable path (press Enter to skip): "
    )
    user_data_dir = _prompt_optional_path(
        "Browser user data dir (press Enter to skip): "
    )

    logger.debug(
        "[cli] collected browser_executable_path={} user_data_dir={}",
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
    # 把浏览器上下文工作流结果转换成终端可读日志，便于快速判断最终模式。
    print()
    print(_build_section_line(" Browser Context Result "))

    if result.success:
        logger.info("[result] final mode: {}", result.resolved_mode)
    else:
        logger.warning("[result] browser context workflow failed")

    if result.used_fallback:
        logger.info("[result] fallback was used")

    if result.reason:
        logger.info("[result] reason: {}", result.reason)

    logger.debug("[result] requested_mode={}", result.requested_mode)
    logger.debug("[result] resolved_mode={}", result.resolved_mode)
    logger.debug("[result] success={}", result.success)
    logger.debug("[result] used_fallback={}", result.used_fallback)
    logger.debug("[result] fallback_chain={}", " -> ".join(result.fallback_chain))

    for message in result.messages:
        if message.startswith("Current attempt mode:"):
            logger.debug("[flow] {}", message)
        else:
            logger.info("[flow] {}", message)

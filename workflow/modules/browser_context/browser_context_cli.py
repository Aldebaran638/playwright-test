import time
from pathlib import Path
from typing import Callable, Literal

from loguru import logger

from workflow.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    get_default_browser_context_config_path,
    load_browser_context_user_input_from_config,
)


InputCollectionMode = Literal["config", "manual"]
DEFAULT_INPUT_TIMEOUT_SECONDS = 15


def _build_section_line(title: str, width: int = 52) -> str:
    return f"{title:-^{width}}"


def _prompt_optional_path(prompt_text: str) -> str | None:
    # 允许用户直接回车跳过当前路径输入。
    user_value = input(prompt_text).strip()
    return user_value or None


def _select_input_mode_with_countdown(
    config_available: bool,
    timeout_seconds: int = DEFAULT_INPUT_TIMEOUT_SECONDS,
) -> InputCollectionMode | None:
    # 给用户一个短暂倒计时决定使用配置模式还是手动模式。
    if not config_available:
        print("未检测到可用配置，将直接进入手动输入模式。")
        return "manual"

    prompt = "输入 m 使用手动模式，输入 c 使用配置模式，回车或超时默认配置模式"
    try:
        import msvcrt
    except ImportError:
        print(f"{prompt}：", end="", flush=True)
        user_value = input().strip().lower()
        if user_value == "m":
            return "manual"
        return "config"

    for remaining in range(timeout_seconds, 0, -1):
        print(f"\r{prompt}，倒计时 {remaining:02d}s ", end="", flush=True)
        deadline = time.time() + 1
        while time.time() < deadline:
            if msvcrt.kbhit():
                key = msvcrt.getwch().strip().lower()
                print()
                if key == "m":
                    return "manual"
                return "config"
            time.sleep(0.05)

    print()
    return None


def collect_browser_context_user_input(
    config_path: str | Path | None = None,
    input_timeout_seconds: int = DEFAULT_INPUT_TIMEOUT_SECONDS,
    mode_selector: Callable[[bool, int], InputCollectionMode | None] | None = None,
    config_loader: Callable[[str | Path | None], BrowserContextUserInput] | None = None,
    prompt_optional_path: Callable[[str], str | None] | None = None,
) -> BrowserContextUserInput:
    # 优先支持配置模式，同时保留手动输入模式和超时回落。
    resolved_config_path = Path(config_path) if config_path else get_default_browser_context_config_path()
    config_loader = config_loader or load_browser_context_user_input_from_config
    prompt_optional_path = prompt_optional_path or _prompt_optional_path
    mode_selector = mode_selector or _select_input_mode_with_countdown

    config_input = config_loader(resolved_config_path).normalized()
    config_available = config_input.has_any_value()

    print()
    print(_build_section_line(" Browser Context Input "))
    print(f"配置文件路径: {resolved_config_path}")
    print("支持两种输入方式：")
    print("1. 配置模式：直接读取配置文件中的浏览器路径和用户数据目录")
    print("2. 手动模式：在终端重新输入路径")
    print()

    logger.info("[cli] collect browser context inputs with config path={}", resolved_config_path)
    selected_mode = mode_selector(config_available, input_timeout_seconds)
    if selected_mode in {None, "config"} and config_available:
        logger.info("[cli] browser context input mode resolved to config")
        return config_input

    if selected_mode == "config" and not config_available:
        logger.warning("[cli] config mode requested but config is empty, fallback to manual mode")

    logger.info("[cli] browser context input mode resolved to manual")
    browser_executable_path = prompt_optional_path(
        "Browser executable path (press Enter to skip): "
    )
    user_data_dir = prompt_optional_path(
        "Browser user data dir (press Enter to skip): "
    )
    return BrowserContextUserInput(
        browser_executable_path=browser_executable_path,
        user_data_dir=user_data_dir,
    ).normalized()


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

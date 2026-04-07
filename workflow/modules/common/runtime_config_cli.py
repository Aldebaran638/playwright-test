import sys

from loguru import logger

from workflow.modules.common.runtime_config import (
    WorkflowRuntimeConfig,
    is_debug_mode,
    set_runtime_config,
)


def _build_header_line(title: str, width: int = 52) -> str:
    return f"{title:=^{width}}"


def _prompt_yes_no(prompt_text: str, default: bool = False) -> bool:
    # 统一解析终端里的 yes/no 输入。
    default_hint = "Y/n" if default else "y/N"
    raw_value = input(f"{prompt_text} [{default_hint}]: ").strip().lower()
    if not raw_value:
        return default
    return raw_value in {"y", "yes", "1", "true"}


def configure_cli_logger() -> None:
    # 根据调试模式统一设置 CLI 日志输出等级。
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if is_debug_mode() else "INFO",
        format="{time:HH:mm:ss} | {level} | {message}",
    )


def collect_runtime_config() -> WorkflowRuntimeConfig:
    # 在工作流开始前收集全局运行参数，并立即应用到日志配置。
    print()
    print(_build_header_line(" Workflow Setup "))
    print("This front-end only collects runtime parameters.")
    print("The browser-context module will probe and downgrade automatically.")
    print()

    debug_mode = _prompt_yes_no("Enable debug mode?", default=False)
    config = WorkflowRuntimeConfig(debug_mode=debug_mode)
    set_runtime_config(config)
    configure_cli_logger()

    logger.info("[config] debug mode {}", "enabled" if debug_mode else "disabled")
    logger.debug("[config] runtime config: {}", config)
    return config

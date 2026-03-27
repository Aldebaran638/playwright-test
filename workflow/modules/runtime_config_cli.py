import sys

from loguru import logger

from workflow.modules.runtime_config import WorkflowRuntimeConfig, is_debug_mode, set_runtime_config


def _build_header_line(title: str, width: int = 52) -> str:
    return f"{title:=^{width}}"


def _prompt_yes_no(prompt_text: str, default: bool = False) -> bool:
    default_hint = "Y/n" if default else "y/N"
    raw_value = input(f"{prompt_text} [{default_hint}]: ").strip().lower()
    if not raw_value:
        return default
    return raw_value in {"y", "yes", "1", "true"}


def configure_cli_logger() -> None:
    """根据全局运行时配置统一设置日志输出等级。"""
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if is_debug_mode() else "INFO",
        format="{time:HH:mm:ss} | {level} | {message}",
    )


def collect_runtime_config() -> WorkflowRuntimeConfig:
    """在整个工作流开始前收集全局运行配置。"""
    print()
    print(_build_header_line(" Workflow Setup "))
    print("这个前端只收集运行参数，不负责业务判断。")
    print("后续浏览器环境模块会根据你的输入自动探测与降级。")
    print()

    debug_mode = _prompt_yes_no("是否开启调试模式", default=False)
    config = WorkflowRuntimeConfig(debug_mode=debug_mode)
    set_runtime_config(config)
    configure_cli_logger()

    logger.info("[配置] 调试模式已{}", "开启" if debug_mode else "关闭")
    logger.debug("[配置] 当前运行时配置: {}", config)
    return config

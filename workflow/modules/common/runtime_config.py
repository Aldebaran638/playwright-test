from dataclasses import dataclass


@dataclass
class WorkflowRuntimeConfig:
    debug_mode: bool = False


_RUNTIME_CONFIG = WorkflowRuntimeConfig()


def set_runtime_config(config: WorkflowRuntimeConfig) -> None:
    # 更新全局运行时配置，供 CLI 和模块日志等级统一读取。
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config


def get_runtime_config() -> WorkflowRuntimeConfig:
    # 返回当前全局运行时配置。
    return _RUNTIME_CONFIG


def is_debug_mode() -> bool:
    # 读取当前是否处于调试模式。
    return _RUNTIME_CONFIG.debug_mode

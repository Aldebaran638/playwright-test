from dataclasses import dataclass


@dataclass
class WorkflowRuntimeConfig:
    debug_mode: bool = False


_RUNTIME_CONFIG = WorkflowRuntimeConfig()


def set_runtime_config(config: WorkflowRuntimeConfig) -> None:
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config


def get_runtime_config() -> WorkflowRuntimeConfig:
    return _RUNTIME_CONFIG


def is_debug_mode() -> bool:
    return _RUNTIME_CONFIG.debug_mode

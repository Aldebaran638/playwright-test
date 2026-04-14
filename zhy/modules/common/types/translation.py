from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OpenAICompatibleClientConfig:
    """简介：描述 OpenAI 格式兼容接口调用所需配置。
    参数：包含 base_url、api_key、model、超时与重试设置。
    返回值：无。
    逻辑：由流程文件统一注入，通用客户端只消费这些参数。
    """

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    retry_count: int
    retry_backoff_base_seconds: float


@dataclass(slots=True)
class PatentAbstractTranslationConfig:
    """简介：描述专利摘要翻译阶段所需配置。
    参数：包含输入输出目录、开关、并发数、目标语言与客户端配置。
    返回值：无。
    逻辑：翻译模块只负责把已有补充摘要转换成中文输出。
    """

    input_root: Path
    output_root: Path
    enabled: bool
    resume: bool
    request_concurrency: int
    target_language: str
    client: OpenAICompatibleClientConfig | None

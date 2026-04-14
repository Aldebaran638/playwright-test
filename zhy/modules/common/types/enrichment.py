from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExistingOutputEnrichmentConfig:
    """简介：描述现有 hybrid 输出补充流程所需的全部配置。
    参数：包含输入输出目录、鉴权文件、请求模板、节流与重试配置。
    返回值：无。
    逻辑：由流程文件统一构建后传入模块，避免模块内部硬编码业务参数。
    """

    input_root: Path
    output_root: Path
    auth_state_file: Path
    cookie_file: Path
    browser_executable_path: str | None
    user_data_dir: str | None
    target_home_url: str
    success_url: str
    success_header_selector: str
    success_logged_in_selector: str
    success_content_selector: str
    loading_overlay_selector: str
    goto_timeout_ms: int
    login_timeout_seconds: float
    login_poll_interval_seconds: float
    capture_timeout_ms: int
    max_auth_refreshes: int
    headless: bool
    timeout_seconds: float
    retry_count: int
    retry_backoff_base_seconds: float
    request_concurrency: int
    min_request_interval_seconds: float
    request_jitter_seconds: float
    resume: bool
    proxy: str | None
    user_agent: str
    x_api_version: str
    x_site_lang: str
    analytics_origin: str
    analytics_referer: str
    analytics_x_patsnap_from: str
    abstract_request_url: str
    abstract_request_template: dict
    basic_request_body_template: dict
    target_page_files: list[Path] | None = None
    summary_path: Path | None = None

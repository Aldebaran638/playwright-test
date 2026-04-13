from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CompetitorPatentPipelineConfig:
    """简介：描述竞争对手专利月报总流程当前阶段所需的全部配置。
    参数：包含登录、后续列表抓取、补充信息和报表输出的默认路径与页面参数。
    返回值：无。
    逻辑：由 task 统一注入所有参数；当前只执行登录步骤，其余参数先保留给后续流程拼接。
    """

    month: str
    browser_executable_path: str | None
    user_data_dir: str | None
    cookie_file: Path
    auth_state_file: Path
    original_output_root: Path
    enriched_output_root: Path
    folder_mapping_file: Path
    folder_mapping_raw_file: Path
    legal_status_mapping_file: Path
    report_output_dir: Path
    pipeline_output_dir: Path
    workspace_space_id: str
    competitor_parent_folder_id: str
    competitor_list_page_url: str
    competitor_list_request_url: str
    workspace_origin: str
    workspace_referer: str
    workspace_x_site_lang: str
    workspace_x_api_version: str
    workspace_x_patsnap_from: str
    workspace_user_agent: str
    analytics_origin: str
    analytics_referer: str
    analytics_x_patsnap_from: str
    abstract_request_url: str
    abstract_request_template: dict
    basic_request_body_template: dict
    enrichment_resume: bool
    enrichment_request_concurrency: int
    target_home_url: str
    success_url: str
    success_header_selector: str
    success_logged_in_selector: str
    success_content_selector: str
    loading_overlay_selector: str
    goto_timeout_ms: int
    login_timeout_seconds: float
    login_poll_interval_seconds: float
    competitor_list_capture_timeout_ms: int
    patents_start_page: int
    patents_page_size: int
    patents_sort: str
    patents_view_type: str
    patents_is_init: bool
    patents_standard_only: bool
    patents_timeout_seconds: float
    patents_capture_timeout_ms: int
    patents_max_auth_refreshes: int
    patents_retry_count: int
    patents_retry_backoff_base_seconds: float
    patents_min_request_interval_seconds: float
    patents_request_jitter_seconds: float
    patents_proxy: str | None
    patents_company_concurrency: int
    patents_test_folder_ids: list[str]
    headless: bool

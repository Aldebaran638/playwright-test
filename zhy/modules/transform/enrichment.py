from __future__ import annotations

from zhy.modules.common.types.enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.common.types.folder_patents import FolderAuthState, HybridTaskConfig
from zhy.modules.fetch.folder_patents_abstract import build_abstract_headers


def build_enrichment_auth_refresh_config(config: ExistingOutputEnrichmentConfig) -> HybridTaskConfig:
    return HybridTaskConfig(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
        cookie_file=config.cookie_file,
        auth_state_file=config.auth_state_file,
        output_root=config.output_root,
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        login_timeout_seconds=config.login_timeout_seconds,
        login_poll_interval_seconds=config.login_poll_interval_seconds,
        origin=config.analytics_origin,
        referer=config.analytics_referer,
        x_site_lang=config.x_site_lang,
        x_api_version=config.x_api_version,
        x_patsnap_from=config.analytics_x_patsnap_from,
        user_agent=config.user_agent,
        abstract_request_url=config.abstract_request_url,
        abstract_origin=config.analytics_origin,
        abstract_referer=config.analytics_referer,
        abstract_x_patsnap_from=config.analytics_x_patsnap_from,
        abstract_request_template=config.abstract_request_template,
        abstract_text_field_name="ABST",
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=100,
        timeout_seconds=config.timeout_seconds,
        capture_timeout_ms=config.capture_timeout_ms,
        max_auth_refreshes=config.max_auth_refreshes,
        retry_count=config.retry_count,
        retry_backoff_base_seconds=config.retry_backoff_base_seconds,
        min_request_interval_seconds=config.min_request_interval_seconds,
        request_jitter_seconds=config.request_jitter_seconds,
        resume=config.resume,
        proxy=config.proxy,
        headless=config.headless,
        fail_fast=False,
    )


def build_enrichment_request_headers(
    config: ExistingOutputEnrichmentConfig,
    auth_state: FolderAuthState,
) -> tuple[dict[str, str], dict[str, str]]:
    abstract_headers = build_abstract_headers(
        auth_state=auth_state,
        origin=config.analytics_origin,
        referer=config.analytics_referer,
        user_agent=config.user_agent,
        x_api_version=config.x_api_version,
        x_patsnap_from=config.analytics_x_patsnap_from,
        x_site_lang=config.x_site_lang,
    )
    basic_headers = dict(abstract_headers)
    return abstract_headers, basic_headers

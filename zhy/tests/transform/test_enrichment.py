import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.transform.enrichment import (
    build_enrichment_auth_refresh_config,
    build_enrichment_request_headers
)
from zhy.modules.common.types.enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.common.types.folder_patents import FolderAuthState


# 本测试文件用于验证 enrichment 模块的核心行为是否符合预期。
# 整体测试思路是：验证数据富集相关的配置构建功能是否正确。
#
# 具体测试方案包括：
# 1. 鉴权刷新配置构建：验证是否能正确构建鉴权刷新配置
# 2. 请求头构建：验证是否能正确构建富集请求头
class TestEnrichment(unittest.TestCase):
    # 测试是否能正确构建鉴权刷新配置
    def test_builds_enrichment_auth_refresh_config_correctly(self) -> None:
        mock_config = MagicMock(spec=ExistingOutputEnrichmentConfig)
        mock_config.browser_executable_path = "test_path"
        mock_config.user_data_dir = "test_data"
        mock_config.cookie_file = MagicMock()
        mock_config.auth_state_file = MagicMock()
        mock_config.output_root = MagicMock()
        mock_config.target_home_url = "http://example.com"
        mock_config.success_url = "http://example.com/success"
        mock_config.success_header_selector = "#header"
        mock_config.success_logged_in_selector = "#login"
        mock_config.success_content_selector = "#content"
        mock_config.loading_overlay_selector = "#loading"
        mock_config.goto_timeout_ms = 10000
        mock_config.login_timeout_seconds = 60.0
        mock_config.login_poll_interval_seconds = 1.0
        mock_config.analytics_origin = "http://example.com"
        mock_config.analytics_referer = "http://example.com/referer"
        mock_config.x_site_lang = "zh-CN"
        mock_config.x_api_version = "1.0"
        mock_config.analytics_x_patsnap_from = "test"
        mock_config.user_agent = "test-agent"
        mock_config.abstract_request_url = "http://example.com/abstract"
        mock_config.abstract_request_template = {}
        mock_config.timeout_seconds = 30.0
        mock_config.capture_timeout_ms = 10000
        mock_config.max_auth_refreshes = 3
        mock_config.retry_count = 3
        mock_config.retry_backoff_base_seconds = 1.0
        mock_config.min_request_interval_seconds = 0.1
        mock_config.request_jitter_seconds = 0.1
        mock_config.resume = False
        mock_config.proxy = None
        mock_config.headless = True
        
        result = build_enrichment_auth_refresh_config(mock_config)
        
        # 验证关键属性
        self.assertEqual(result.browser_executable_path, "test_path")
        self.assertEqual(result.user_data_dir, "test_data")
        self.assertEqual(result.cookie_file, mock_config.cookie_file)
        self.assertEqual(result.auth_state_file, mock_config.auth_state_file)
        self.assertEqual(result.output_root, mock_config.output_root)
        self.assertEqual(result.target_home_url, "http://example.com")
        self.assertEqual(result.success_url, "http://example.com/success")
        self.assertEqual(result.abstract_text_field_name, "ABST")
        self.assertEqual(result.start_page, 1)
        self.assertEqual(result.max_pages, None)
        self.assertEqual(result.page_concurrency, 1)
        self.assertEqual(result.size, 100)
        self.assertEqual(result.fail_fast, False)
    
    # 测试是否能正确构建富集请求头
    def test_builds_enrichment_request_headers_correctly(self) -> None:
        mock_config = MagicMock(spec=ExistingOutputEnrichmentConfig)
        mock_config.analytics_origin = "http://example.com"
        mock_config.analytics_referer = "http://example.com/referer"
        mock_config.user_agent = "test-agent"
        mock_config.x_api_version = "1.0"
        mock_config.analytics_x_patsnap_from = "test"
        mock_config.x_site_lang = "zh-CN"
        
        mock_auth_state = MagicMock(spec=FolderAuthState)
        mock_auth_state.to_headers = MagicMock(return_value={"Authorization": "Bearer token"})
        
        abstract_headers, basic_headers = build_enrichment_request_headers(mock_config, mock_auth_state)
        
        mock_auth_state.to_headers.assert_called_once()
        self.assertEqual(abstract_headers, {"Authorization": "Bearer token"})
        self.assertEqual(basic_headers, {"Authorization": "Bearer token"})


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.fetch.folder_patents_auth import (
    build_folder_page_url,
    build_cookie_header_from_cookie_list,
    is_matching_patents_request
)


# 本测试文件用于验证 folder_patents_auth 模块的核心行为是否符合预期。
# 整体测试思路是：验证 URL 构建、Cookie 头构建和请求判断功能是否正确。
#
# 具体测试方案包括：
# 1. URL 构建：验证是否能正确构建 workspace 专利表页 URL
# 2. Cookie 头构建：验证是否能正确将 cookies 列表转换为 Cookie 请求头
# 3. 请求判断：验证是否能正确判断目标文件夹的 patents API 请求
class TestFolderPatentsAuth(unittest.TestCase):
    # 测试是否能正确构建 workspace 专利表页 URL
    def test_builds_folder_page_url_correctly(self) -> None:
        space_id = "space123"
        folder_id = "folder456"
        page = 1
        
        expected_url = f"https://workspace.zhihuiya.com/detail/patent/table?spaceId={space_id}&folderId={folder_id}&page={page}"
        result = build_folder_page_url(space_id, folder_id, page)
        
        self.assertEqual(result, expected_url)
    
    # 测试当 cookies 列表有效时，是否能正确构建 Cookie 请求头
    def test_returns_cookie_header_when_cookies_are_valid(self) -> None:
        cookies = [
            {"name": "cookie1", "value": "value1"},
            {"name": "cookie2", "value": "value2"}
        ]
        
        expected_header = "cookie1=value1; cookie2=value2"
        result = build_cookie_header_from_cookie_list(cookies)
        
        self.assertEqual(result, expected_header)
    
    # 测试当 cookies 列表为空时，是否返回 None
    def test_returns_empty_result_when_cookies_are_empty(self) -> None:
        cookies = []
        result = build_cookie_header_from_cookie_list(cookies)
        self.assertIsNone(result)
    
    # 测试当 cookie 缺少 name 字段时，是否能正确跳过
    def test_skips_cookie_when_required_field_is_missing(self) -> None:
        cookies = [
            {"name": "cookie1", "value": "value1"},
            {"value": "value2"},  # 缺少 name
            {"name": "cookie3", "value": "value3"}
        ]
        
        expected_header = "cookie1=value1; cookie3=value3"
        result = build_cookie_header_from_cookie_list(cookies)
        
        self.assertEqual(result, expected_header)
    
    # 测试当 cookie 值为 None 时，是否能正确处理
    def test_handles_invalid_cookie_value_gracefully(self) -> None:
        cookies = [
            {"name": "cookie1", "value": None},
            {"name": "cookie2", "value": "value2"}
        ]
        
        expected_header = "cookie1=; cookie2=value2"
        result = build_cookie_header_from_cookie_list(cookies)
        
        self.assertEqual(result, expected_header)
    
    # 测试是否能正确判断目标文件夹的 patents API 请求
    def test_identifies_matching_patents_request_correctly(self) -> None:
        space_id = "space123"
        folder_id = "folder456"
        
        # 匹配的请求
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url = f"https://workspace-service.zhihuiya.com/workspace/web/{space_id}/folder/{folder_id}/patents"
        
        result = is_matching_patents_request(mock_request, space_id, folder_id)
        self.assertTrue(result)
        
        # 方法不匹配
        mock_request.method = "GET"
        result = is_matching_patents_request(mock_request, space_id, folder_id)
        self.assertFalse(result)
        
        # 域名不匹配
        mock_request.method = "POST"
        mock_request.url = f"https://other-domain.com/workspace/web/{space_id}/folder/{folder_id}/patents"
        result = is_matching_patents_request(mock_request, space_id, folder_id)
        self.assertFalse(result)
        
        # 路径不匹配
        mock_request.url = f"https://workspace-service.zhihuiya.com/workspace/web/other_space/folder/{folder_id}/patents"
        result = is_matching_patents_request(mock_request, space_id, folder_id)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

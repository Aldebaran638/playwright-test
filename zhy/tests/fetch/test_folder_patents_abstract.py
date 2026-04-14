import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.fetch.folder_patents_abstract import (
    build_abstract_headers,
    build_abstract_request_body,
    extract_abstract_text,
    summarize_abstract_payload
)
from zhy.modules.common.types.folder_patents import FolderAuthState


# 本测试文件用于验证 folder_patents_abstract 模块的核心行为是否符合预期。
# 整体测试思路是：验证摘要接口的请求构建和响应处理功能是否正确。
#
# 具体测试方案包括：
# 1. 请求头构建：验证是否能正确构建摘要接口请求头
# 2. 请求体构建：验证是否能正确构建摘要请求体
# 3. 摘要提取：验证是否能正确从响应中提取摘要文本
# 4. 摘要摘要：验证是否能正确提取摘要响应的调试摘要
class TestFolderPatentsAbstract(unittest.TestCase):
    # 测试是否能正确构建摘要接口请求头
    def test_builds_abstract_headers_correctly(self) -> None:
        mock_auth_state = MagicMock(spec=FolderAuthState)
        mock_auth_state.to_headers = MagicMock(return_value={"Authorization": "Bearer token"})
        
        result = build_abstract_headers(
            auth_state=mock_auth_state,
            origin="http://example.com",
            referer="http://example.com/referer",
            user_agent="test-agent",
            x_api_version="1.0",
            x_patsnap_from="test",
            x_site_lang="zh-CN"
        )
        
        mock_auth_state.to_headers.assert_called_once()
        self.assertEqual(result, {"Authorization": "Bearer token"})
    
    # 测试是否能正确构建摘要请求体
    def test_builds_abstract_request_body_correctly(self) -> None:
        template = {"key1": "value1", "key2": "value2"}
        patent_id = "CN123456789"
        folder_id = "folder123"
        workspace_id = "workspace123"
        
        result = build_abstract_request_body(
            template=template,
            patent_id=patent_id,
            folder_id=folder_id,
            workspace_id=workspace_id
        )
        
        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["key2"], "value2")
        self.assertEqual(result["patent_id"], patent_id)
        self.assertEqual(result["folder_id"], folder_id)
        self.assertEqual(result["workspace_id"], workspace_id)
        # 验证模板没有被修改
        self.assertEqual(template, {"key1": "value1", "key2": "value2"})
    
    # 测试当 payload 有效时，是否能正确提取摘要文本
    def test_extracts_abstract_when_payload_is_valid(self) -> None:
        # 从 translation 字段提取
        payload = {
            "data": {
                "translation": "这是摘要文本"
            }
        }
        result = extract_abstract_text(payload)
        self.assertEqual(result, "这是摘要文本")
        
        # 从 text 字段提取
        payload = {
            "data": {
                "text": "这是摘要文本"
            }
        }
        result = extract_abstract_text(payload)
        self.assertEqual(result, "这是摘要文本")
        
        # 从嵌套结构提取
        payload = {
            "data": {
                "nested": {
                    "text": "这是嵌套摘要文本"
                }
            }
        }
        result = extract_abstract_text(payload)
        self.assertEqual(result, "这是嵌套摘要文本")
    
    # 测试当摘要缺失时，是否返回空字符串
    def test_returns_empty_result_when_abstract_is_missing(self) -> None:
        # 空 payload
        result = extract_abstract_text({})
        self.assertEqual(result, "")
        
        # 缺少数据
        result = extract_abstract_text({"data": None})
        self.assertEqual(result, "")
        
        # 空字符串
        result = extract_abstract_text({"data": {"text": ""}})
        self.assertEqual(result, "")
        
        # 无效值
        result = extract_abstract_text({"data": {"text": "null"}})
        self.assertEqual(result, "")
    
    # 测试是否能正确提取摘要响应的调试摘要
    def test_summarizes_abstract_payload_correctly(self) -> None:
        payload = {
            "data": {
                "translation": "这是摘要文本",
                "other_key": "other_value"
            },
            "status": "success"
        }
        
        result = summarize_abstract_payload(payload)
        self.assertEqual(result["top_level_keys"], ["data", "status"])
        self.assertEqual(result["data_type"], "dict")
        self.assertIn("data_keys", result)
        self.assertIn("data.translation.type", result)
        self.assertIn("data.translation.preview", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.fetch.competitor_folder_mapping import (
    filter_competitor_folder_items,
    build_filtered_folder_mapping_payload,
    is_target_competitor_list_response
)
from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig


# 本测试文件用于验证 competitor_folder_mapping 模块的核心行为是否符合预期。
# 整体测试思路是：验证文件夹项过滤、映射构建和响应判断功能是否正确。
#
# 具体测试方案包括：
# 1. 文件夹项过滤：验证是否能正确过滤出指定父文件夹的项目
# 2. 映射构建：验证是否能正确构建过滤后的文件夹映射 payload
# 3. 响应判断：验证是否能正确判断目标竞争对手列表响应
class TestCompetitorFolderMapping(unittest.TestCase):
    # 测试是否能正确过滤出指定父文件夹的项目
    def test_filters_competitor_folder_items_correctly(self) -> None:
        parent_folder_id = "parent123"
        payload = {
            "data": [
                {"id": "1", "parent_id": "parent123", "name": "Competitor 1"},
                {"id": "2", "parent_id": "other", "name": "Competitor 2"},
                {"id": "3", "name": "Competitor 3"}  # 缺少 parent_id
            ]
        }
        
        result = filter_competitor_folder_items(payload, parent_folder_id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[0]["parent_id"], "parent123")
    
    # 测试当 payload 格式不正确时，是否返回空列表
    def test_returns_empty_list_for_invalid_payload(self) -> None:
        parent_folder_id = "parent123"
        
        # 非字典 payload
        result = filter_competitor_folder_items("invalid", parent_folder_id)
        self.assertEqual(len(result), 0)
        
        # 缺少 data 字段
        result = filter_competitor_folder_items({}, parent_folder_id)
        self.assertEqual(len(result), 0)
        
        # data 不是列表
        result = filter_competitor_folder_items({"data": "not a list"}, parent_folder_id)
        self.assertEqual(len(result), 0)
    
    # 测试是否能正确构建过滤后的文件夹映射 payload
    def test_builds_filtered_folder_mapping_payload_correctly(self) -> None:
        config = MagicMock(spec=CompetitorPatentPipelineConfig)
        config.workspace_space_id = "space123"
        config.competitor_parent_folder_id = "parent123"
        
        filtered_items = [{"id": "1", "name": "Competitor 1"}]
        
        result = build_filtered_folder_mapping_payload(config, filtered_items)
        
        self.assertTrue(result["status"])
        self.assertEqual(result["space_id"], "space123")
        self.assertEqual(result["parent_folder_id"], "parent123")
        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["id"], "1")
    
    # 测试是否能正确判断目标竞争对手列表响应
    def test_identifies_target_competitor_list_response_correctly(self) -> None:
        test_url = "http://example.com/api/competitors"
        
        # 匹配的响应
        mock_response = MagicMock()
        mock_response.request.method = "GET"
        mock_response.url = test_url
        
        result = is_target_competitor_list_response(mock_response, test_url)
        self.assertTrue(result)
        
        # 方法不匹配
        mock_response.request.method = "POST"
        result = is_target_competitor_list_response(mock_response, test_url)
        self.assertFalse(result)
        
        # URL 不匹配
        mock_response.request.method = "GET"
        mock_response.url = "http://example.com/api/other"
        result = is_target_competitor_list_response(mock_response, test_url)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

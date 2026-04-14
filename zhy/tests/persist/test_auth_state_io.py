import sys
import unittest
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.persist.auth_state_io import load_auth_state_if_valid, load_auth_state_from_file
from zhy.modules.common.types.folder_patents import FolderAuthState


# 本测试文件用于验证 auth_state_io 模块的核心行为是否符合预期。
# 整体测试思路是：通过创建临时文件，验证鉴权状态的加载和校验功能是否正确。
#
# 具体测试方案包括：
# 1. 成功加载场景：验证当鉴权状态文件存在且有效时，是否能正确加载
# 2. 文件不存在场景：验证当鉴权状态文件不存在时，是否返回 None
# 3. 无效内容场景：验证当鉴权状态文件内容无效时，是否返回 None
# 4. 空间/文件夹不匹配场景：验证当空间或文件夹 ID 不匹配时，是否返回 None
# 5. 缺少必要字段场景：验证当缺少必要字段时，是否返回 None
class TestAuthStateIO(unittest.TestCase):
    # 测试当鉴权状态文件存在且有效时，是否能正确加载
    def test_loads_auth_state_successfully_when_file_is_valid(self) -> None:
        test_auth_state = {
            "space_id": "test_space",
            "folder_id": "test_folder",
            "request_url": "http://example.com",
            "authorization": "Bearer token",
            "x_client_id": "client_id",
            "x_device_id": "device_id",
            "b3": "trace_id",
            "cookie_header": "cookie1=value1; cookie2=value2",
            "body_template": {"page": 1},
            "captured_at": "2026-01-01T00:00:00Z"
        }
        
        test_path = Path("test_auth_state.json")
        test_path.write_text(json.dumps(test_auth_state), encoding="utf-8")
        
        try:
            result = load_auth_state_if_valid(test_path, "test_space", "test_folder")
            self.assertIsInstance(result, FolderAuthState)
            self.assertEqual(result.space_id, "test_space")
            self.assertEqual(result.folder_id, "test_folder")
        finally:
            if test_path.exists():
                test_path.unlink()
    
    # 测试当鉴权状态文件不存在时，是否返回 None
    def test_returns_none_when_auth_state_file_does_not_exist(self) -> None:
        non_existent_path = Path("non_existent_auth_state.json")
        if non_existent_path.exists():
            non_existent_path.unlink()
        
        result = load_auth_state_if_valid(non_existent_path, "test_space", "test_folder")
        self.assertIsNone(result)
    
    # 测试当鉴权状态文件内容无效时，是否返回 None
    def test_returns_none_when_auth_state_file_is_invalid(self) -> None:
        test_path = Path("test_invalid_auth_state.json")
        test_path.write_text("invalid json", encoding="utf-8")
        
        try:
            result = load_auth_state_if_valid(test_path, "test_space", "test_folder")
            self.assertIsNone(result)
        finally:
            if test_path.exists():
                test_path.unlink()
    
    # 测试当空间或文件夹 ID 不匹配时，是否返回 None
    def test_returns_none_when_space_or_folder_id_mismatch(self) -> None:
        test_auth_state = {
            "space_id": "test_space",
            "folder_id": "test_folder",
            "request_url": "http://example.com",
            "authorization": "Bearer token",
            "x_client_id": "client_id",
            "x_device_id": "device_id",
            "b3": "trace_id",
            "cookie_header": "cookie1=value1; cookie2=value2",
            "body_template": {"page": 1},
            "captured_at": "2026-01-01T00:00:00Z"
        }
        
        test_path = Path("test_auth_state_mismatch.json")
        test_path.write_text(json.dumps(test_auth_state), encoding="utf-8")
        
        try:
            # 空间 ID 不匹配
            result = load_auth_state_if_valid(test_path, "wrong_space", "test_folder")
            self.assertIsNone(result)
            
            # 文件夹 ID 不匹配
            result = load_auth_state_if_valid(test_path, "test_space", "wrong_folder")
            self.assertIsNone(result)
        finally:
            if test_path.exists():
                test_path.unlink()
    
    # 测试当缺少必要字段时，是否返回 None
    def test_returns_none_when_required_fields_are_missing(self) -> None:
        test_auth_state = {
            "space_id": "test_space",
            "folder_id": "test_folder",
            "request_url": "",  # 缺少请求 URL
            "authorization": None,
            "x_client_id": None,
            "x_device_id": None,
            "b3": None,
            "cookie_header": None,
            "body_template": {},
            "captured_at": "2026-01-01T00:00:00Z"
        }
        
        test_path = Path("test_auth_state_missing_fields.json")
        test_path.write_text(json.dumps(test_auth_state), encoding="utf-8")
        
        try:
            result = load_auth_state_if_valid(test_path, "test_space", "test_folder")
            self.assertIsNone(result)
        finally:
            if test_path.exists():
                test_path.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)

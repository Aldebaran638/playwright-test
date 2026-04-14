import sys
import unittest
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.persist.json_io import save_json, load_json_file_any_utf


# 本测试文件用于验证 json_io 模块的核心行为是否符合预期。
# 整体测试思路是：通过创建临时文件，验证 JSON 文件的读写功能是否正确。
#
# 具体测试方案包括：
# 1. 成功读取场景：验证当 JSON 文件存在且有效时，是否能正确读取
# 2. 文件不存在场景：验证当 JSON 文件不存在时，是否会抛出异常
# 3. 无效 JSON 场景：验证当 JSON 文件内容无效时，是否会抛出异常
# 4. 成功写入场景：验证是否能正确将数据写入 JSON 文件
class TestJsonIO(unittest.TestCase):
    # 测试当 JSON 文件存在且有效时，是否能正确读取
    def test_loads_json_successfully_when_file_is_valid(self) -> None:
        test_data = {"key": "value"}
        test_path = Path("test_valid.json")
        test_path.write_text(json.dumps(test_data), encoding="utf-8")
        
        try:
            result = load_json_file_any_utf(test_path)
            self.assertEqual(result, test_data)
        finally:
            if test_path.exists():
                test_path.unlink()
    
    # 测试当 JSON 文件不存在时，是否会抛出异常
    def test_raises_error_when_json_file_does_not_exist(self) -> None:
        non_existent_path = Path("non_existent.json")
        if non_existent_path.exists():
            non_existent_path.unlink()
        
        with self.assertRaises(FileNotFoundError):
            load_json_file_any_utf(non_existent_path)
    
    # 测试当 JSON 文件内容无效时，是否会抛出异常
    def test_raises_error_when_json_content_is_invalid(self) -> None:
        test_path = Path("test_invalid.json")
        test_path.write_text("invalid json", encoding="utf-8")
        
        try:
            with self.assertRaises(json.JSONDecodeError):
                load_json_file_any_utf(test_path)
        finally:
            if test_path.exists():
                test_path.unlink()
    
    # 测试是否能正确将数据写入 JSON 文件
    def test_saves_json_successfully(self) -> None:
        test_data = {"key": "value"}
        test_path = Path("test_save.json")
        if test_path.exists():
            test_path.unlink()
        
        try:
            save_json(test_path, test_data)
            self.assertTrue(test_path.exists())
            saved_data = json.loads(test_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_data, test_data)
        finally:
            if test_path.exists():
                test_path.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)

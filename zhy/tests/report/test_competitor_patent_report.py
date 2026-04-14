import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.report.competitor_patent_report import (
    validate_month_text,
    normalize_text,
    normalize_line_wrapped_text,
    parse_folder_key,
    resolve_legal_status_text,
    make_report_title,
    excel_column_name
)


# 本测试文件用于验证 competitor_patent_report 模块的核心行为是否符合预期。
# 整体测试思路是：验证报表生成相关的辅助功能是否正确。
#
# 具体测试方案包括：
# 1. 月份验证：验证是否能正确验证月份格式
# 2. 文本规范化：验证是否能正确规范化文本
# 3. 文件夹键解析：验证是否能正确解析文件夹键
# 4. 法律状态映射：验证是否能正确解析法律状态
# 5. 报表标题生成：验证是否能正确生成报表标题
# 6. Excel 列名生成：验证是否能正确生成 Excel 列名
class TestCompetitorPatentReport(unittest.TestCase):
    # 测试是否能正确验证月份格式
    def test_validates_month_text_correctly(self) -> None:
        # 有效格式
        validate_month_text("2026-01")
        validate_month_text("2026-12")
        
        # 无效格式
        with self.assertRaises(ValueError):
            validate_month_text("2026/01")
        with self.assertRaises(ValueError):
            validate_month_text("202601")
        with self.assertRaises(ValueError):
            validate_month_text("2026")
    
    # 测试是否能正确规范化文本
    def test_normalizes_text_correctly(self) -> None:
        # 字符串
        self.assertEqual(normalize_text("  test  text  "), "test text")
        self.assertEqual(normalize_text("test\ntext"), "test text")
        
        # 数字
        self.assertEqual(normalize_text(123), "123")
        
        # 布尔值
        self.assertEqual(normalize_text(True), "True")
        
        # 列表
        self.assertEqual(normalize_text(["test1", "test2"]), "test1；test2")
        
        # None
        self.assertEqual(normalize_text(None), "")
    
    # 测试是否能正确规范化换行文本
    def test_normalizes_line_wrapped_text_correctly(self) -> None:
        # 列表
        self.assertEqual(normalize_line_wrapped_text(["test1", "test2"]), "test1；test2")
        
        # 字符串
        self.assertEqual(normalize_line_wrapped_text("test text"), "test text")
    
    # 测试是否能正确解析文件夹键
    def test_parses_folder_key_correctly(self) -> None:
        # 包含下划线
        space_id, folder_id = parse_folder_key("space123_folder456")
        self.assertEqual(space_id, "space123")
        self.assertEqual(folder_id, "folder456")
        
        # 不包含下划线
        space_id, folder_id = parse_folder_key("folder456")
        self.assertEqual(space_id, "")
        self.assertEqual(folder_id, "folder456")
    
    # 测试是否能正确解析法律状态
    def test_resolves_legal_status_text_correctly(self) -> None:
        mapping = {"1": "有效", "2": "无效", "3": "授权"}
        
        # 单个状态码
        self.assertEqual(resolve_legal_status_text("1", mapping), "有效")
        
        # 状态码列表
        self.assertEqual(resolve_legal_status_text(["1", "3"], mapping), "有效；授权")
        
        # 无效状态码
        self.assertEqual(resolve_legal_status_text("999", mapping), "")
        
        # 空值
        self.assertEqual(resolve_legal_status_text(None, mapping), "")
    
    # 测试是否能正确生成报表标题
    def test_makes_report_title_correctly(self) -> None:
        self.assertEqual(make_report_title("2026-01"), "竞争对手专利情报(2026年1月)")
        self.assertEqual(make_report_title("2026-12"), "竞争对手专利情报(2026年12月)")
    
    # 测试是否能正确生成 Excel 列名
    def test_generates_excel_column_name_correctly(self) -> None:
        self.assertEqual(excel_column_name(1), "A")
        self.assertEqual(excel_column_name(26), "Z")
        self.assertEqual(excel_column_name(27), "AA")
        self.assertEqual(excel_column_name(28), "AB")


if __name__ == "__main__":
    unittest.main(verbosity=2)

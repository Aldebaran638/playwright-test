import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.persist.page_path import (
    build_patents_page_path,
    build_patents_summary_path,
    build_monthly_page_output_path,
    build_monthly_run_summary_path,
    build_enrichment_page_path,
    iter_input_page_files,
    iter_folder_page_files,
    has_existing_page_files,
    parse_space_folder_from_parent
)


# 本测试文件用于验证 page_path 模块的核心行为是否符合预期。
# 整体测试思路是：验证各种路径构建函数是否能正确生成预期的文件路径。
#
# 具体测试方案包括：
# 1. 专利页面路径构建：验证是否能正确构建专利页面文件路径
# 2. 专利摘要路径构建：验证是否能正确构建专利摘要文件路径
# 3. 月度页面输出路径构建：验证是否能正确构建月度页面输出文件路径
# 4. 月度运行摘要路径构建：验证是否能正确构建月度运行摘要文件路径
# 5. 富集页面路径构建：验证是否能正确构建富集页面文件路径
# 6. 空间和文件夹解析：验证是否能正确从父文件夹名称解析空间和文件夹 ID
class TestPagePath(unittest.TestCase):
    # 测试是否能正确构建专利页面文件路径
    def test_builds_patents_page_path_correctly(self) -> None:
        output_root = Path("test_output")
        space_id = "test_space"
        folder_id = "test_folder"
        page = 1
        
        expected_path = output_root / f"{space_id}_{folder_id}" / "page_0001.json"
        result = build_patents_page_path(output_root, space_id, folder_id, page)
        
        self.assertEqual(result, expected_path)
    
    # 测试是否能正确构建专利摘要文件路径
    def test_builds_patents_summary_path_correctly(self) -> None:
        output_root = Path("test_output")
        space_id = "test_space"
        
        expected_path = output_root / f"{space_id}_run_summary.json"
        result = build_patents_summary_path(output_root, space_id)
        
        self.assertEqual(result, expected_path)
    
    # 测试是否能正确构建月度页面输出文件路径
    def test_builds_monthly_page_output_path_correctly(self) -> None:
        output_root = Path("test_output")
        space_id = "test_space"
        folder_id = "test_folder"
        source_page_number = 1
        
        expected_path = output_root / f"{space_id}_{folder_id}" / "page_0001.json"
        result = build_monthly_page_output_path(output_root, space_id, folder_id, source_page_number)
        
        self.assertEqual(result, expected_path)
    
    # 测试是否能正确构建月度运行摘要文件路径
    def test_builds_monthly_run_summary_path_correctly(self) -> None:
        output_root = Path("test_output")
        month_text = "2026-01"
        
        expected_path = output_root / "monthly_patents_2026_01_run_summary.json"
        result = build_monthly_run_summary_path(output_root, month_text)
        
        self.assertEqual(result, expected_path)
    
    # 测试是否能正确构建富集页面文件路径
    def test_builds_enrichment_page_path_correctly(self) -> None:
        output_root = Path("test_output")
        input_root = Path("test_input")
        page_file = input_root / "space_folder" / "page_0001.json"
        
        expected_path = output_root / "space_folder" / "page_0001.json"
        result = build_enrichment_page_path(output_root, input_root, page_file)
        
        self.assertEqual(result, expected_path)
    
    # 测试是否能正确从父文件夹名称解析空间和文件夹 ID
    def test_parses_space_folder_from_parent_correctly(self) -> None:
        # 正常情况：包含下划线的文件夹名
        folder_dir = Path("space_id_folder_id")
        space_id, folder_id = parse_space_folder_from_parent(folder_dir)
        self.assertEqual(space_id, "space_id")
        self.assertEqual(folder_id, "folder_id")
        
        # 边界情况：不包含下划线的文件夹名
        folder_dir = Path("folder_id")
        space_id, folder_id = parse_space_folder_from_parent(folder_dir)
        self.assertEqual(space_id, "")
        self.assertEqual(folder_id, "folder_id")


if __name__ == "__main__":
    unittest.main(verbosity=2)

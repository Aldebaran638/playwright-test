import sys
import unittest
from pathlib import Path
from datetime import date


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.fetch.monthly_patents import (
    parse_month_bounds,
    parse_publication_date,
    is_date_in_target_month,
    filter_patents_for_target_month,
    get_page_publication_date_bounds,
    build_monthly_patents_request_body,
    build_monthly_page_output_payload,
    filter_folder_items_for_test
)


# 本测试文件用于验证 monthly_patents 模块的核心行为是否符合预期。
# 整体测试思路是：验证月度专利数据的处理和过滤功能是否正确。
#
# 具体测试方案包括：
# 1. 月份边界解析：验证是否能正确解析月份边界
# 2. 公开日期解析：验证是否能正确解析专利公开日期
# 3. 日期过滤：验证是否能正确判断日期是否在目标月份
# 4. 专利过滤：验证是否能正确过滤目标月份的专利
# 5. 日期边界获取：验证是否能正确获取页面专利的日期边界
# 6. 请求体构建：验证是否能正确构建月度专利请求体
# 7. 输出构建：验证是否能正确构建月度页面输出
# 8. 文件夹过滤：验证是否能正确过滤测试文件夹
class TestMonthlyPatents(unittest.TestCase):
    # 测试是否能正确解析月份边界
    def test_parses_month_bounds_correctly(self) -> None:
        # 测试1月
        start, end = parse_month_bounds("2026-01")
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 2, 1))
        
        # 测试12月
        start, end = parse_month_bounds("2026-12")
        self.assertEqual(start, date(2026, 12, 1))
        self.assertEqual(end, date(2027, 1, 1))
    
    # 测试是否能正确解析专利公开日期
    def test_parses_publication_date_correctly(self) -> None:
        # 有效日期
        result = parse_publication_date("2026-01-01")
        self.assertEqual(result, date(2026, 1, 1))
        
        # 无效日期
        self.assertIsNone(parse_publication_date("2026-01"))
        self.assertIsNone(parse_publication_date("invalid"))
        self.assertIsNone(parse_publication_date(None))
    
    # 测试是否能正确判断日期是否在目标月份
    def test_identifies_date_in_target_month_correctly(self) -> None:
        month_start = date(2026, 1, 1)
        next_month_start = date(2026, 2, 1)
        
        # 边界情况：月初
        self.assertTrue(is_date_in_target_month(date(2026, 1, 1), month_start, next_month_start))
        
        # 边界情况：月末
        self.assertTrue(is_date_in_target_month(date(2026, 1, 31), month_start, next_month_start))
        
        # 边界情况：下月月初
        self.assertFalse(is_date_in_target_month(date(2026, 2, 1), month_start, next_month_start))
        
        # 中间日期
        self.assertTrue(is_date_in_target_month(date(2026, 1, 15), month_start, next_month_start))
        
        # 上月日期
        self.assertFalse(is_date_in_target_month(date(2025, 12, 31), month_start, next_month_start))
    
    # 测试是否能正确过滤目标月份的专利
    def test_filters_patents_for_target_month_correctly(self) -> None:
        rows = [
            {"PBD": "2026-01-15"},  # 目标月份
            {"PBD": "2026-02-01"},  # 下月
            {"PBD": "2025-12-31"},  # 上月
            {"PBD": "invalid"},     # 无效日期
            {"other": "field"}       # 缺少 PBD
        ]
        
        month_start = date(2026, 1, 1)
        next_month_start = date(2026, 2, 1)
        
        result = filter_patents_for_target_month(rows, month_start, next_month_start)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["PBD"], "2026-01-15")
    
    # 测试是否能正确获取页面专利的日期边界
    def test_gets_page_publication_date_bounds_correctly(self) -> None:
        rows = [
            {"PBD": "2026-01-15"},
            {"PBD": "2026-01-10"},
            {"PBD": "2026-01-20"}
        ]
        
        newest, oldest = get_page_publication_date_bounds(rows)
        self.assertEqual(newest, date(2026, 1, 20))
        self.assertEqual(oldest, date(2026, 1, 10))
        
        # 空列表
        newest, oldest = get_page_publication_date_bounds([])
        self.assertIsNone(newest)
        self.assertIsNone(oldest)
    
    # 测试是否能正确构建月度专利请求体
    def test_builds_monthly_patents_request_body_correctly(self) -> None:
        template = {"key1": "value1"}
        space_id = "space123"
        folder_id = "folder456"
        page = 1
        size = 20
        sort = "desc"
        view_type = "table"
        is_init = True
        standard_only = True
        
        result = build_monthly_patents_request_body(
            template,
            space_id=space_id,
            folder_id=folder_id,
            page=page,
            size=size,
            sort=sort,
            view_type=view_type,
            is_init=is_init,
            standard_only=standard_only
        )
        
        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["space_id"], space_id)
        self.assertEqual(result["folder_id"], folder_id)
        self.assertEqual(result["page"], page)
        self.assertEqual(result["size"], size)
        self.assertEqual(result["sort"], sort)
        self.assertEqual(result["view_type"], view_type)
        self.assertEqual(result["is_init"], is_init)
        self.assertEqual(result["standard_only"], standard_only)
    
    # 测试是否能正确构建月度页面输出
    def test_builds_monthly_page_output_payload_correctly(self) -> None:
        parsed = {"data": {"patents_data": [1, 2, 3]}}
        matched_rows = [{"PBD": "2026-01-15"}]
        source_page_number = 1
        month_text = "2026-01"
        
        result = build_monthly_page_output_payload(
            parsed, matched_rows, source_page_number, month_text
        )
        
        self.assertEqual(result["data"]["patents_data"], matched_rows)
        self.assertEqual(result["data"]["month_filter"], month_text)
        self.assertEqual(result["data"]["source_page_number"], source_page_number)
        self.assertEqual(result["data"]["matched_patent_count"], len(matched_rows))
    
    # 测试是否能正确过滤测试文件夹
    def test_filters_folder_items_for_test_correctly(self) -> None:
        folder_items = [
            {"folder_id": "1", "folder_name": "Company 1"},
            {"folder_id": "2", "folder_name": "Company 2"},
            {"folder_id": "3", "folder_name": "Company 3"}
        ]
        
        # 白名单为空，返回全部
        result = filter_folder_items_for_test(folder_items, [])
        self.assertEqual(len(result), 3)
        
        # 白名单过滤
        result = filter_folder_items_for_test(folder_items, ["1", "3"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["folder_id"], "1")
        self.assertEqual(result[1]["folder_id"], "3")


if __name__ == "__main__":
    unittest.main(verbosity=2)

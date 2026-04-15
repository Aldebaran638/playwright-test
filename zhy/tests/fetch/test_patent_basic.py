import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.fetch.patent_basic import (
    build_basic_request_url,
    build_basic_request_body,
    extract_grant_date_from_basic_payload,
    extract_abstract_from_basic_payload,
    extract_supplemental_legal_status_from_basic_payload,
    strip_html_text,
    _has_granted_status
)


# 本测试文件用于验证 patent_basic 模块的核心行为是否符合预期。
# 整体测试思路是：验证专利基本信息的提取和处理功能是否正确。
#
# 具体测试方案包括：
# 1. URL 构建：验证是否能正确构建专利 basic 接口 URL
# 2. 请求体构建：验证是否能正确构建请求体
# 3. 授权日期提取：验证是否能正确从 payload 中提取授权日期
# 4. 摘要提取：验证是否能正确从 payload 中提取摘要
# 5. HTML 清洗：验证是否能正确清洗 HTML 标签
# 6. 授权状态判断：验证是否能正确判断专利授权状态
class TestPatentBasic(unittest.TestCase):
    # 测试是否能正确构建专利 basic 接口 URL
    def test_builds_basic_request_url_correctly(self) -> None:
        patent_id = "CN123456789"
        expected_url = f"https://search-service.zhihuiya.com/core-search-api/search/patent/id/{patent_id}/basic?highlight=true"
        result = build_basic_request_url(patent_id=patent_id)
        self.assertEqual(result, expected_url)
    
    # 测试是否能正确构建请求体
    def test_builds_basic_request_body_correctly(self) -> None:
        template = {"key1": "value1", "key2": "value2"}
        patent_id = "CN123456789"
        
        result = build_basic_request_body(template=template, patent_id=patent_id)
        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["key2"], "value2")
        self.assertEqual(result["patent_id"], patent_id)
        # 验证模板没有被修改
        self.assertEqual(template, {"key1": "value1", "key2": "value2"})
    
    # 测试当 payload 有效时，是否能正确提取授权日期
    def test_extracts_grant_date_when_payload_is_valid(self) -> None:
        # 从 timeline 中提取
        payload = {
            "data": {
                "timeline": [
                    {"type": "ISD", "date": "2020-01-01"},
                    {"type": "Other", "date": "2019-01-01"}
                ]
            }
        }
        result = extract_grant_date_from_basic_payload(payload)
        self.assertEqual(result, "2020-01-01")
        
        # 从 ISD 字段提取
        payload = {
            "data": {
                "ISD": "2020-01-01"
            }
        }
        result = extract_grant_date_from_basic_payload(payload)
        self.assertEqual(result, "2020-01-01")
    
    # 测试当字段缺失时，是否返回空字符串
    def test_returns_empty_string_when_grant_date_is_missing(self) -> None:
        # 空 payload
        result = extract_grant_date_from_basic_payload({})
        self.assertEqual(result, "")
        
        # 缺少 data
        result = extract_grant_date_from_basic_payload({"data": None})
        self.assertEqual(result, "")
        
        # 缺少 timeline 和 ISD
        result = extract_grant_date_from_basic_payload({"data": {}})
        self.assertEqual(result, "")
    
    # 测试当 payload 有效时，是否能正确提取摘要
    def test_extracts_abstract_when_payload_is_valid(self) -> None:
        # 从 ABST.CN 提取
        payload = {
            "data": {
                "ABST": {
                    "CN": "中文摘要",
                    "EN": "English abstract"
                }
            }
        }
        result = extract_abstract_from_basic_payload(payload)
        self.assertEqual(result, "中文摘要")
        
        # 从 ABST.EN 提取（当 CN 不存在时）
        payload = {
            "data": {
                "ABST": {
                    "EN": "English abstract"
                }
            }
        }
        result = extract_abstract_from_basic_payload(payload)
        self.assertEqual(result, "English abstract")
        
        # 从 ABST 字符串提取
        payload = {
            "data": {
                "ABST": "直接摘要"
            }
        }
        result = extract_abstract_from_basic_payload(payload)
        self.assertEqual(result, "直接摘要")
    
    # 测试当摘要缺失时，是否返回空字符串
    def test_returns_empty_string_when_abstract_is_missing(self) -> None:
        # 空 payload
        result = extract_abstract_from_basic_payload({})
        self.assertEqual(result, "")
        
        # 缺少 data
        result = extract_abstract_from_basic_payload({"data": None})
        self.assertEqual(result, "")
        
        # 缺少 ABST
        result = extract_abstract_from_basic_payload({"data": {}})
        self.assertEqual(result, "")
    
    # 测试是否能正确清洗 HTML 标签
    def test_strips_html_text_correctly(self) -> None:
        html_text = "<p>这是 <b>HTML</b> 文本</p>"
        expected_text = "这是 HTML 文本"
        result = strip_html_text(html_text)
        self.assertEqual(result, expected_text)
    
    # 测试是否能正确判断专利授权状态
    def test_identifies_granted_status_correctly(self) -> None:
        # 列表中包含 "3"
        self.assertTrue(_has_granted_status(["1", "3", "5"]))
        # 直接是 "3"
        self.assertTrue(_has_granted_status("3"))
        # 不包含 "3"
        self.assertFalse(_has_granted_status(["1", "2", "4"]))
        # 不是 "3"
        self.assertFalse(_has_granted_status("2"))


    def test_extracts_supplemental_legal_status_as_granted_when_timeline_has_isd(self) -> None:
        payload = {
            "data": {
                "timeline": [
                    {"date": "2026-03-30", "type": ["OPN_PBD", "ISD"]}
                ]
            }
        }
        result = extract_supplemental_legal_status_from_basic_payload(payload)
        self.assertEqual(result, "授权")

    def test_extracts_supplemental_legal_status_as_published_when_timeline_has_no_isd(self) -> None:
        payload = {
            "data": {
                "timeline": [
                    {"date": "2023-02-17", "type": ["F_PBD"]}
                ]
            }
        }
        result = extract_supplemental_legal_status_from_basic_payload(payload)
        self.assertEqual(result, "公开")
if __name__ == "__main__":
    unittest.main(verbosity=2)

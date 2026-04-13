import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_patents_enrichment.basic_fetch import (
    build_basic_request_body,
    build_basic_request_url,
    extract_abstract_from_basic_payload,
    extract_grant_date_from_basic_payload,
)
from zhy.modules.folder_patents_enrichment.workflow import has_granted_status


class TestBasicFetch(unittest.TestCase):
    def test_build_basic_request_url_embeds_patent_id(self) -> None:
        url = build_basic_request_url(patent_id="pat-1")
        self.assertEqual(
            url,
            "https://search-service.zhihuiya.com/core-search-api/search/patent/id/pat-1/basic?highlight=true",
        )

    def test_build_basic_request_body_keeps_template_immutable(self) -> None:
        template = {"lang": "CN", "highlight": True}
        body = build_basic_request_body(template=template, patent_id="pat-1")
        self.assertEqual(body["patent_id"], "pat-1")
        self.assertEqual(template, {"lang": "CN", "highlight": True})

    def test_extract_grant_date_prefers_timeline_isd(self) -> None:
        payload = {
            "data": {
                "ISD": "fallback",
                "timeline": [
                    {"date": "2018-01-01", "type": ["APD"]},
                    {"date": "2020-01-03", "type": ["OPN_PBD", "ISD"]},
                ],
            }
        }
        self.assertEqual(extract_grant_date_from_basic_payload(payload), "2020-01-03")

    def test_extract_grant_date_falls_back_to_top_level_isd(self) -> None:
        payload = {"data": {"ISD": "2021-02-03"}}
        self.assertEqual(extract_grant_date_from_basic_payload(payload), "2021-02-03")

    def test_extract_abstract_prefers_cn_and_strips_html(self) -> None:
        payload = {
            "data": {
                "ABST": {
                    "EN": "english abstract",
                    "CN": "<div p='0' i='0'>中文摘要</div>",
                }
            }
        }
        self.assertEqual(extract_abstract_from_basic_payload(payload), "中文摘要")

    def test_extract_abstract_falls_back_to_first_available_language(self) -> None:
        payload = {
            "data": {
                "ABST": {
                    "JP": "<div>日本語要約</div>",
                    "DE": "de text",
                }
            }
        }
        self.assertEqual(extract_abstract_from_basic_payload(payload), "日本語要約")

    def test_has_granted_status_detects_code_3(self) -> None:
        self.assertTrue(has_granted_status([61, 3]))
        self.assertFalse(has_granted_status([61, 17]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

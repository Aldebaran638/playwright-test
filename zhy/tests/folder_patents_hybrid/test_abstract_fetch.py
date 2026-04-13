import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_patents_hybrid.abstract_fetch import (
    build_abstract_request_body,
    enrich_page_patents_with_abstracts,
    extract_abstract_text,
)
from zhy.modules.folder_patents_hybrid.api_fetch import RequestScheduler


class TestAbstractFetch(unittest.IsolatedAsyncioTestCase):
    def test_build_abstract_request_body_injects_runtime_ids(self) -> None:
        template = {
            "field": "ABST",
            "lang": "CN",
        }

        body = build_abstract_request_body(
            template=template,
            patent_id="pat-1",
            folder_id="folder-1",
            workspace_id="space-1",
        )

        self.assertEqual(body["patent_id"], "pat-1")
        self.assertEqual(body["folder_id"], "folder-1")
        self.assertEqual(body["workspace_id"], "space-1")
        self.assertEqual(template, {"field": "ABST", "lang": "CN"})

    def test_extract_abstract_text_prefers_nested_translation_fields(self) -> None:
        payload = {
            "status": True,
            "data": {
                "translation": {
                    "text": "这是摘要文本",
                }
            },
        }

        self.assertEqual(extract_abstract_text(payload), "这是摘要文本")

    async def test_enrich_page_patents_with_abstracts_updates_rows_and_records_failures(self) -> None:
        page_payload = {
            "data": {
                "patents_data": [
                    {"PATENT_ID": "pat-1", "TITLE": "title-1"},
                    {"PATENT_ID": "pat-2", "TITLE": "title-2"},
                    {"TITLE": "missing id"},
                    {"PATENT_ID": "pat-3", "ABST_TEXT": "already exists"},
                ]
            }
        }

        async def fake_fetcher(**kwargs) -> str:
            patent_id = kwargs["patent_id"]
            if patent_id == "pat-2":
                raise RuntimeError("boom")
            return f"abstract for {patent_id}"

        failures = await enrich_page_patents_with_abstracts(
            page_payload=page_payload,
            text_field_name="ABST_TEXT",
            request_url="https://example.test/abstract",
            request_template={"field": "ABST"},
            request_headers={"authorization": "Bearer token"},
            folder_id="folder-1",
            workspace_id="space-1",
            timeout_seconds=10.0,
            proxies=None,
            scheduler=RequestScheduler(concurrency=1, min_interval_seconds=0.0, jitter_seconds=0.0),
            retry_count=1,
            retry_backoff_base_seconds=0.1,
            fetcher=fake_fetcher,
        )

        rows = page_payload["data"]["patents_data"]
        self.assertEqual(rows[0]["ABST_TEXT"], "abstract for pat-1")
        self.assertNotIn("ABST_TEXT", rows[1])
        self.assertEqual(rows[3]["ABST_TEXT"], "already exists")
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0]["patent_id"], "pat-2")
        self.assertEqual(failures[1]["reason"], "missing_patent_id")


if __name__ == "__main__":
    unittest.main(verbosity=2)

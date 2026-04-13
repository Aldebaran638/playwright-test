import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.competitor_patent_pipeline.models import CompetitorPatentPipelineConfig
from zhy.modules.competitor_patent_pipeline.workflow import (
    build_competitor_patent_report_config,
    build_existing_output_enrichment_config,
    build_pipeline_summary_payload,
    filter_competitor_folder_items,
    run_competitor_patent_pipeline,
)


class TestCompetitorPatentPipelineWorkflow(unittest.TestCase):
    def build_config(self) -> CompetitorPatentPipelineConfig:
        root = Path("C:/demo")
        return CompetitorPatentPipelineConfig(
            month="2026-04",
            browser_executable_path="browser.exe",
            user_data_dir="user-data",
            cookie_file=root / "cookies.json",
            auth_state_file=root / "auth.json",
            original_output_root=root / "original",
            enriched_output_root=root / "enriched",
            folder_mapping_file=root / "mid3.filtered.json",
            folder_mapping_raw_file=root / "mid3.raw.json",
            legal_status_mapping_file=root / "mid1.json",
            report_output_dir=root / "reports",
            pipeline_output_dir=root / "pipeline",
            workspace_space_id="ccb6031b05034c7ab2c4b120c2dc3155",
            competitor_parent_folder_id="8614f137547f4e46b8557ae8d3b1e1f5",
            competitor_list_page_url="https://workspace.zhihuiya.com/detail/patent/default?spaceId=ccb6031b05034c7ab2c4b120c2dc3155",
            competitor_list_request_url="https://workspace-service.zhihuiya.com/workspace/web/space/ccb6031b05034c7ab2c4b120c2dc3155/folder-list",
            workspace_origin="https://workspace.zhihuiya.com",
            workspace_referer="https://workspace.zhihuiya.com/",
            workspace_x_site_lang="CN",
            workspace_x_api_version="2.0",
            workspace_x_patsnap_from="w-analytics-workspace",
            workspace_user_agent="Mozilla/5.0",
            analytics_origin="https://analytics.zhihuiya.com",
            analytics_referer="https://analytics.zhihuiya.com/",
            analytics_x_patsnap_from="w-analytics-patent-view",
            abstract_request_url="https://search-service.zhihuiya.com/core-search-api/search/translate/patent",
            abstract_request_template={"field": "ABST"},
            basic_request_body_template={"product": "Analytics"},
            enrichment_resume=True,
            enrichment_request_concurrency=5,
            target_home_url="https://analytics.zhihuiya.com/request_demo?project=search#/template",
            success_url="https://analytics.zhihuiya.com/request_demo?project=search#/template",
            success_header_selector="#header-wrapper",
            success_logged_in_selector=".patsnap-biz-user_center--logged .patsnap-biz-avatar",
            success_content_selector="#demo_user-info",
            loading_overlay_selector="#page-pre-loading-bg",
            goto_timeout_ms=30000,
            login_timeout_seconds=600.0,
            login_poll_interval_seconds=3.0,
            competitor_list_capture_timeout_ms=45000,
            patents_start_page=1,
            patents_page_size=100,
            patents_sort="pdesc",
            patents_view_type="tablelist",
            patents_is_init=True,
            patents_standard_only=False,
            patents_timeout_seconds=30.0,
            patents_capture_timeout_ms=45000,
            patents_max_auth_refreshes=5,
            patents_retry_count=3,
            patents_retry_backoff_base_seconds=1.0,
            patents_min_request_interval_seconds=1.2,
            patents_request_jitter_seconds=0.4,
            patents_proxy=None,
            patents_company_concurrency=1,
            patents_test_folder_ids=[],
            headless=False,
        )

    def test_build_pipeline_summary_payload_marks_following_steps_pending(self) -> None:
        payload = build_pipeline_summary_payload(
            self.build_config(),
            login_status="done",
            login_final_url="https://analytics.zhihuiya.com/request_demo?project=search#/template",
            competitor_list_status="done",
            competitor_list_count=2,
            competitor_list_output="C:/demo/mid3.filtered.json",
            monthly_patents_status="done",
            monthly_patents_folder_count=2,
            monthly_patents_output="C:/demo/monthly_summary.json",
            enrich_patents_status="done",
            enrich_patents_output="C:/demo/enrichment_summary.json",
            enrich_patents_pages_written=5,
            build_monthly_report_status="done",
            build_monthly_report_output="C:/demo/report.xlsx",
        )

        self.assertEqual(payload["month"], "2026-04")
        self.assertEqual(payload["steps"][0]["name"], "login")
        self.assertEqual(payload["steps"][0]["status"], "done")
        self.assertEqual(payload["steps"][1]["status"], "done")
        self.assertEqual(payload["steps"][1]["count"], 2)
        self.assertEqual(payload["steps"][2]["status"], "done")
        self.assertEqual(payload["steps"][2]["folder_count"], 2)
        self.assertEqual(payload["steps"][3]["status"], "done")
        self.assertEqual(payload["steps"][3]["pages_written"], 5)
        self.assertEqual(payload["steps"][4]["status"], "done")
        self.assertEqual(payload["steps"][4]["output"], "C:/demo/report.xlsx")

    def test_build_existing_output_enrichment_config_reuses_pipeline_values(self) -> None:
        config = build_existing_output_enrichment_config(self.build_config())

        self.assertEqual(config.input_root, Path("C:/demo/original"))
        self.assertEqual(config.output_root, Path("C:/demo/enriched"))
        self.assertEqual(config.analytics_origin, "https://analytics.zhihuiya.com")
        self.assertEqual(config.analytics_x_patsnap_from, "w-analytics-patent-view")
        self.assertTrue(config.resume)
        self.assertEqual(config.request_concurrency, 5)

    def test_build_competitor_patent_report_config_reuses_pipeline_values(self) -> None:
        config = build_competitor_patent_report_config(self.build_config())

        self.assertEqual(config.month, "2026-04")
        self.assertEqual(config.original_root, Path("C:/demo/original"))
        self.assertEqual(config.enriched_root, Path("C:/demo/enriched"))
        self.assertEqual(config.output_dir, Path("C:/demo/reports"))

    def test_filter_competitor_folder_items_keeps_only_target_parent(self) -> None:
        payload = {
            "data": [
                {"folder_id": "root", "parent_id": "-root", "folder_name": "竞争对手监控"},
                {"folder_id": "a", "parent_id": "8614f137547f4e46b8557ae8d3b1e1f5", "folder_name": "甲"},
                {"folder_id": "b", "parent_id": "8614f137547f4e46b8557ae8d3b1e1f5", "folder_name": "乙"},
                {"folder_id": "c", "parent_id": "other", "folder_name": "丙"},
            ]
        }

        filtered = filter_competitor_folder_items(payload, "8614f137547f4e46b8557ae8d3b1e1f5")

        self.assertEqual([item["folder_id"] for item in filtered], ["a", "b"])


class TestCompetitorPatentPipelineWorkflowExecution(unittest.IsolatedAsyncioTestCase):
    def build_config(self, root: Path) -> CompetitorPatentPipelineConfig:
        return CompetitorPatentPipelineConfig(
            month="2026-04",
            browser_executable_path="browser.exe",
            user_data_dir="user-data",
            cookie_file=root / "cookies.json",
            auth_state_file=root / "auth.json",
            original_output_root=root / "original",
            enriched_output_root=root / "enriched",
            folder_mapping_file=root / "mid3.filtered.json",
            folder_mapping_raw_file=root / "mid3.raw.json",
            legal_status_mapping_file=root / "mid1.json",
            report_output_dir=root / "reports",
            pipeline_output_dir=root / "pipeline",
            workspace_space_id="space-1",
            competitor_parent_folder_id="parent-1",
            competitor_list_page_url="https://workspace.example/list",
            competitor_list_request_url="https://workspace.example/api/folder-list",
            workspace_origin="https://workspace.example",
            workspace_referer="https://workspace.example/",
            workspace_x_site_lang="CN",
            workspace_x_api_version="2.0",
            workspace_x_patsnap_from="w-analytics-workspace",
            workspace_user_agent="Mozilla/5.0",
            analytics_origin="https://analytics.example",
            analytics_referer="https://analytics.example/",
            analytics_x_patsnap_from="w-analytics-patent-view",
            abstract_request_url="https://analytics.example/abstract",
            abstract_request_template={"field": "ABST"},
            basic_request_body_template={"product": "Analytics"},
            enrichment_resume=True,
            enrichment_request_concurrency=5,
            target_home_url="https://analytics.example/home",
            success_url="https://analytics.example/home",
            success_header_selector="#header",
            success_logged_in_selector=".logged",
            success_content_selector="#content",
            loading_overlay_selector="#loading",
            goto_timeout_ms=30000,
            login_timeout_seconds=600.0,
            login_poll_interval_seconds=3.0,
            competitor_list_capture_timeout_ms=45000,
            patents_start_page=1,
            patents_page_size=100,
            patents_sort="pdesc",
            patents_view_type="tablelist",
            patents_is_init=True,
            patents_standard_only=False,
            patents_timeout_seconds=30.0,
            patents_capture_timeout_ms=45000,
            patents_max_auth_refreshes=5,
            patents_retry_count=3,
            patents_retry_backoff_base_seconds=1.0,
            patents_min_request_interval_seconds=1.2,
            patents_request_jitter_seconds=0.4,
            patents_proxy=None,
            patents_company_concurrency=1,
            patents_test_folder_ids=[],
            headless=False,
        )

    async def test_run_competitor_patent_pipeline_runs_enrichment_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.build_config(root)
            enrichment_summary_path = config.enriched_output_root / "run_summary.json"
            report_output_path = config.report_output_dir / "竞争对手专利情报_2026-04.xlsx"
            mapping_path = config.folder_mapping_file
            monthly_summary_path = config.original_output_root / "monthly_patents_2026_04_run_summary.json"
            managed = Mock()
            managed.close = AsyncMock()

            class FakeAsyncPlaywrightContext:
                async def __aenter__(self):
                    return object()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            async def fake_run_existing_output_enrichment(_config):
                enrichment_summary_path.parent.mkdir(parents=True, exist_ok=True)
                enrichment_summary_path.write_text(
                    json.dumps({"pages_written": 3}, ensure_ascii=False),
                    encoding="utf-8",
                )
                return enrichment_summary_path

            with (
                patch("playwright.async_api.async_playwright", return_value=FakeAsyncPlaywrightContext()),
                patch("zhy.modules.browser_context.runtime.build_browser_context", new=AsyncMock(return_value=managed)),
                patch("zhy.modules.competitor_patent_pipeline.workflow.ensure_pipeline_logged_in", new=AsyncMock(return_value="https://analytics.example/home")),
                patch("zhy.modules.competitor_patent_pipeline.workflow.fetch_competitor_folder_mapping", new=AsyncMock(return_value=(mapping_path, 2))),
                patch("zhy.modules.competitor_patent_pipeline.workflow.run_monthly_patent_fetch", new=AsyncMock(return_value=(monthly_summary_path, {"folders": [{}, {}]}))),
                patch("zhy.modules.competitor_patent_pipeline.workflow.run_existing_output_enrichment", new=AsyncMock(side_effect=fake_run_existing_output_enrichment)) as enrichment_mock,
                patch("zhy.modules.competitor_patent_pipeline.workflow.run_competitor_patent_report", return_value=report_output_path) as report_mock,
            ):
                summary_path = await run_competitor_patent_pipeline(config)

            self.assertEqual(summary_path, config.pipeline_output_dir / "competitor_patent_pipeline_2026-04_summary.json")
            self.assertTrue(summary_path.exists())
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["steps"][3]["status"], "done")
            self.assertEqual(payload["steps"][3]["pages_written"], 3)
            self.assertEqual(payload["steps"][4]["status"], "done")
            self.assertEqual(payload["steps"][4]["output"], str(report_output_path))
            enrichment_mock.assert_awaited_once()
            report_mock.assert_called_once()
            managed.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tyc.modules.batch_company_query as batch_company_query_module
from tyc.modules.run_step import StepResult


logger.remove()
logger.add(sys.stdout, format="{message}")


def build_success_step_result(fn, *args, **kwargs):
    kwargs.pop("step_name", None)
    kwargs.pop("critical", None)
    kwargs.pop("retries", None)
    return StepResult(ok=True, value=fn(*args, **kwargs), error=None)


class FakePage:
    def __init__(self, url: str = "https://example.com") -> None:
        self.url = url
        self.closed = False
        self.calls: list[tuple] = []

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.calls.append(("goto", url, wait_until))
        self.url = url

    def wait_for_load_state(self, state: str) -> None:
        self.calls.append(("wait_for_load_state", state))

    def is_closed(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.calls.append(("close",))
        self.closed = True


class TestBatchCompanyQuery(unittest.TestCase):
    def test_query_companies_sequentially_collects_success_results(self) -> None:
        logger.info("[测试1] 验证批量查询模块会按顺序收集多家公司结果")
        home_page = FakePage("https://www.tianyancha.com/")

        def fake_go_home(page, *, home_url):
            page.goto(home_url, wait_until="domcontentloaded")

        def fake_enter(page, company_name):
            return FakePage(f"https://detail.example.com/{company_name}")

        def fake_extract(page, source=None):
            return {"source": source, "company_name": page.url.split("/")[-1]}

        with patch.object(
            batch_company_query_module,
            "run_step",
            side_effect=build_success_step_result,
        ), patch.object(
            batch_company_query_module,
            "go_to_home_page",
            side_effect=fake_go_home,
        ), patch.object(
            batch_company_query_module,
            "enter_company_detail_page",
            side_effect=fake_enter,
        ), patch.object(
            batch_company_query_module,
            "extract_company_metadata",
            side_effect=fake_extract,
        ):
            results = batch_company_query_module.query_companies_sequentially(
                home_page,
                ["小米通讯技术有限公司", "北京小桔科技有限公司"],
            )

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["success"])
        self.assertTrue(results[1]["success"])
        self.assertEqual(results[0]["company_name"], "小米通讯技术有限公司")
        self.assertEqual(results[1]["company_name"], "北京小桔科技有限公司")
        self.assertEqual(
            home_page.calls,
            [
                ("goto", batch_company_query_module.TYC_HOME_URL, "domcontentloaded"),
                ("goto", batch_company_query_module.TYC_HOME_URL, "domcontentloaded"),
            ],
        )

    def test_query_companies_sequentially_continues_after_failure_by_default(self) -> None:
        logger.info("[测试2] 验证批量查询模块默认在单家公司失败后继续处理下一家")
        home_page = FakePage("https://www.tianyancha.com/")

        def fake_go_home(page, *, home_url):
            page.goto(home_url, wait_until="domcontentloaded")

        def fake_enter(page, company_name):
            if company_name == "失败公司":
                raise RuntimeError("boom")
            return FakePage(f"https://detail.example.com/{company_name}")

        def fake_extract(page, source=None):
            return {"source": source}

        def fake_run_step(fn, *args, **kwargs):
            kwargs.pop("step_name", None)
            kwargs.pop("critical", None)
            kwargs.pop("retries", None)
            try:
                return StepResult(ok=True, value=fn(*args, **kwargs), error=None)
            except Exception as exc:
                return StepResult(ok=False, value=None, error=exc)

        with patch.object(
            batch_company_query_module,
            "run_step",
            side_effect=fake_run_step,
        ), patch.object(
            batch_company_query_module,
            "go_to_home_page",
            side_effect=fake_go_home,
        ), patch.object(
            batch_company_query_module,
            "enter_company_detail_page",
            side_effect=fake_enter,
        ), patch.object(
            batch_company_query_module,
            "extract_company_metadata",
            side_effect=fake_extract,
        ):
            results = batch_company_query_module.query_companies_sequentially(
                home_page,
                ["失败公司", "成功公司"],
            )

        self.assertEqual(len(results), 2)
        self.assertFalse(results[0]["success"])
        self.assertTrue(results[1]["success"])
        self.assertEqual(results[0]["error"], "boom")

    def test_query_companies_sequentially_stops_when_stop_on_error_enabled(self) -> None:
        logger.info("[测试3] 验证批量查询模块在 stop_on_error=True 时遇错停止")
        home_page = FakePage("https://www.tianyancha.com/")

        def fake_go_home(page, *, home_url):
            page.goto(home_url, wait_until="domcontentloaded")

        def fake_enter(page, company_name):
            if company_name == "失败公司":
                raise RuntimeError("boom")
            return FakePage(f"https://detail.example.com/{company_name}")

        def fake_run_step(fn, *args, **kwargs):
            kwargs.pop("step_name", None)
            kwargs.pop("critical", None)
            kwargs.pop("retries", None)
            try:
                return StepResult(ok=True, value=fn(*args, **kwargs), error=None)
            except Exception as exc:
                return StepResult(ok=False, value=None, error=exc)

        with patch.object(
            batch_company_query_module,
            "run_step",
            side_effect=fake_run_step,
        ), patch.object(
            batch_company_query_module,
            "go_to_home_page",
            side_effect=fake_go_home,
        ), patch.object(
            batch_company_query_module,
            "enter_company_detail_page",
            side_effect=fake_enter,
        ), patch.object(
            batch_company_query_module,
            "extract_company_metadata",
            side_effect=lambda page, source=None: {"source": source},
        ):
            results = batch_company_query_module.query_companies_sequentially(
                home_page,
                ["失败公司", "不会执行的公司"],
                stop_on_error=True,
            )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

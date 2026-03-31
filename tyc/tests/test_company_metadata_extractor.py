import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from loguru import logger
from playwright.sync_api import Browser, Playwright, sync_playwright


# 兼容直接运行测试脚本时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tyc.modules.company_metadata.extractor as extractor_module
from tyc.modules.run_step import StepResult


logger.remove()
logger.add(sys.stdout, format="{message}")


def build_success_step_result(fn, *args, **kwargs):
    kwargs.pop("step_name", None)
    kwargs.pop("critical", None)
    kwargs.pop("retries", None)
    return StepResult(ok=True, value=fn(*args, **kwargs), error=None)


class TestCompanyMetadataExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("[测试1] 启动 Playwright 浏览器，准备测试 company_metadata_extractor 模块")
        cls.playwright: Playwright = sync_playwright().start()
        cls.browser: Browser = cls.playwright.chromium.launch(headless=True)
        cls.sample_html = """
        <div id="J_CompanyHeaderContent">
            <div class="index_header-top__JbFpN">
                <h1 class="index_company-name__LqKlo">
                    <span class="index_name__dz4jY">小米通讯技术有限公司</span>
                    <div class="index_reg-status-tag__ES7dF">存续</div>
                </h1>
                <div class="index_tag-list-content__E8sLp">
                    <div class="index_company-tag__ZcJFV">高新技术企业</div>
                    <div class="index_company-tag__ZcJFV">科技型中小企业</div>
                </div>
                <div class="Refresh_company-refresh__52K8W"><span>2026-03-21更新</span></div>
            </div>
            <div class="index_detail-info-item__oAOqL">
                <span class="index_detail-label__oRf2J">统一社会信用代码：</span>
                <span>91110108558521630L</span>
            </div>
            <div class="index_detail-info-item__oAOqL">
                <span class="index_detail-label__oRf2J">邮箱：</span>
                <a href="mailto:legal-corpstru@xiaomi.com">legal-corpstru@xiaomi.com</a>
            </div>
            <div class="index_detail-info-item__oAOqL">
                <span class="index_detail-label__oRf2J">网址：</span>
                <a href="https://www.mi.com">www.mi.com</a>
            </div>
            <div class="index_detail-info-item__oAOqL">
                <span class="index_detail-label__oRf2J">地址：</span>
                <span>北京市海淀区西二旗中路33号院6号楼9层019号</span>
            </div>
            <div class="introduceRich_collapse-left__5Vvd5">
                <span class="introduceRich_collapse-title__XzjQz">简介：</span>
                <span>小米通讯技术有限公司成立于2010年。</span>
            </div>
        </div>
        """

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("[测试1] 关闭 Playwright 浏览器")
        cls.browser.close()
        cls.playwright.stop()

    def load_sample_page(self):
        page = self.browser.new_page()
        page.set_content(self.sample_html, wait_until="domcontentloaded")
        return page

    def test_normalize_text(self) -> None:
        logger.info("[测试2] 验证 normalize_text() 能清洗空白和尾部冒号")
        self.assertEqual(extractor_module.normalize_text("  电话：\n"), "电话")
        self.assertEqual(extractor_module.normalize_text("  hello   world  "), "hello world")

    def test_extract_company_metadata_returns_expected_keys(self) -> None:
        logger.info("[测试3] 验证 extract_company_metadata() 返回稳定的顶层字段")
        page = self.load_sample_page()
        try:
            with patch.object(
                extractor_module,
                "run_step",
                side_effect=build_success_step_result,
            ):
                result = extractor_module.extract_company_metadata(page, source="inline-sample")
        finally:
            page.close()

        expected_keys = {
            "company_name",
            "company_status",
            "company_tags",
            "last_update",
            "detail_items",
            "introduction",
            "full_text",
            "page_title",
            "header_text",
            "source",
        }
        self.assertTrue(expected_keys.issubset(result.keys()))
        self.assertEqual(result["source"], "inline-sample")
        self.assertIsInstance(result["detail_items"], dict)
        self.assertIsInstance(result["company_tags"], list)

    def test_extract_company_metadata_reads_core_values(self) -> None:
        logger.info("[测试4] 验证元信息提取模块能提取详情页中的关键值")
        page = self.load_sample_page()
        try:
            with patch.object(
                extractor_module,
                "run_step",
                side_effect=build_success_step_result,
            ):
                result = extractor_module.extract_company_metadata(page, source="inline-sample")
        finally:
            page.close()

        detail_items = result["detail_items"]
        joined_values = " ".join(str(value) for value in detail_items.values())

        self.assertTrue(result["company_name"])
        self.assertRegex(joined_values, r"[0-9A-Z]{18}")
        self.assertRegex(joined_values, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        self.assertRegex(joined_values, r"www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        self.assertRegex(result["last_update"], r"\d{4}-\d{2}-\d{2}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Tests for the Mintel HTML to Markdown converter module."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from loguru import logger

# 允许直接运行当前测试文件时，也能找到 spider_learn 下的模块。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入被测试函数，下面会直接调用它们完成 HTML -> Markdown 转换。
from modules.mintel_html_to_markdown import (
    convert_mintel_html_file_to_markdown,
    save_mintel_markdown,
)

logger.remove()
logger.add(sys.stdout, level="DEBUG")


class MintelHtmlToMarkdownTests(unittest.TestCase):
    def setUp(self) -> None:
        # 使用真实下载样例，确认模块能处理项目里这类 HTML 文件。
        self.sample_html_path = (
            PROJECT_ROOT.parent
            / "downloads"
            / "Chanel Rouge Coco Flash Denim Makeup Hydrating Vibrant Shine Lip Colour.html"
        )

    def test_convert_file_generates_structured_markdown(self) -> None:
        # 直接调用被测试函数，把 HTML 文件转换成结构化 Markdown。
        logger.debug("[测试1] 开始转换 HTML 文件: {path}", path=self.sample_html_path)
        markdown = convert_mintel_html_file_to_markdown(self.sample_html_path)
        logger.debug("[测试1] 生成的 Markdown 字符数: {length}", length=len(markdown))

        self.assertIn("# Hydrating Vibrant Shine Lip Colour", markdown)
        self.assertIn("## 基本信息", markdown)
        self.assertIn("| 字段 | 值 |", markdown)
        self.assertIn("| 公司 | Chanel; Neuilly sur Seine,France |", markdown)
        self.assertIn("## 产品描述", markdown)
        self.assertIn("## 包装信息", markdown)
        self.assertIn("| 字段 | 一级 |", markdown)
        self.assertIn("| 包装类型 | 管 |", markdown)
        self.assertIn("## 图片链接", markdown)
        self.assertIn("https://media.mintel.com/", markdown)
        self.assertIn("## 其他信息", markdown)
        self.assertIn("### 更多此产品的信息", markdown)
        self.assertIn("#### 成分", markdown)
        self.assertIn("#### 定位宣称", markdown)

    def test_save_markdown_writes_md_file(self) -> None:
        # 调用保存函数，确认模块会把转换结果真正写入 .md 文件。
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "converted_product.md"
            logger.debug("[测试2] 开始保存 Markdown 文件: {path}", path=output_path)

            saved_path = save_mintel_markdown(self.sample_html_path, output_path=output_path)
            markdown_text = saved_path.read_text(encoding="utf-8")
            logger.debug("[测试2] 已保存 Markdown，字符数: {length}", length=len(markdown_text))

            self.assertEqual(saved_path, output_path)
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".md")
            self.assertIn("# Hydrating Vibrant Shine Lip Colour", markdown_text)


if __name__ == "__main__":
    # 支持用 python 直接执行当前测试文件。
    unittest.main(verbosity=1)

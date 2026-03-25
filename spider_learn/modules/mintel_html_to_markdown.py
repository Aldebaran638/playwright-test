"""Convert Mintel product HTML files into structured Markdown."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag
from loguru import logger


CORE_SECTION_DESCRIPTION = "产品描述"
CORE_SECTION_PACKAGING = "包装信息"


def convert_mintel_html_to_markdown(html_content: str) -> str:
    """Convert Mintel product HTML content into structured Markdown."""
    logger.debug("[模块] 开始将 HTML 文本转换为 Markdown")
    soup = BeautifulSoup(html_content, "html.parser")
    _replace_line_breaks(soup)

    product_container = soup.select_one(".Product_full_content")
    if product_container is None:
        raise ValueError("Could not find the Mintel product container in HTML content.")

    title = _extract_title(product_container)
    logger.debug("[模块] 解析到产品标题: {title}", title=title)

    markdown_lines: list[str] = [f"# {title}", ""]
    markdown_lines.extend(_build_basic_info_section(product_container))
    markdown_lines.extend(_build_core_sections(product_container))
    markdown_lines.extend(_build_image_section(product_container))

    other_info_lines = _build_other_info_section(product_container)
    if other_info_lines:
        markdown_lines.extend(other_info_lines)

    markdown = "\n".join(markdown_lines).strip() + "\n"
    logger.debug("[模块] Markdown 转换完成，总字符数: {length}", length=len(markdown))
    return markdown


def convert_mintel_html_file_to_markdown(html_path: str | Path) -> str:
    """Load a Mintel HTML file from disk and convert it into Markdown."""
    html_file = Path(html_path)
    logger.debug("[模块] 读取 HTML 文件: {path}", path=html_file)
    return convert_mintel_html_to_markdown(html_file.read_text(encoding="utf-8"))


def save_mintel_markdown(
    html_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Convert a Mintel HTML file and save the Markdown result to disk."""
    html_file = Path(html_path)
    target_path = Path(output_path) if output_path is not None else html_file.with_suffix(".md")

    markdown = convert_mintel_html_file_to_markdown(html_file)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown, encoding="utf-8")
    logger.debug("[模块] 已保存 Markdown 文件: {path}", path=target_path)
    return target_path


def _replace_line_breaks(soup: BeautifulSoup) -> None:
    for line_break in soup.find_all("br"):
        line_break.replace_with("\n")


def _extract_title(product_container: Tag) -> str:
    title_node = product_container.select_one(".Product_top_section h1")
    if title_node is None:
        raise ValueError("Could not find the product title in HTML content.")
    return _normalize_inline_text(title_node.get_text(" ", strip=True))


def _build_basic_info_section(product_container: Tag) -> list[str]:
    section_lines = ["## 基本信息", ""]
    basic_table = product_container.select_one(".Product_top_section .detail_container table")
    if basic_table is None:
        logger.debug("[模块] 未找到基本信息表，跳过该部分")
        return section_lines + ["| 字段 | 值 |", "|---|---|", ""]

    section_lines.extend(["| 字段 | 值 |", "|---|---|"])

    last_field_name: str | None = None
    last_field_index: int | None = None

    for row in basic_table.find_all("tr", recursive=False):
        header_cell = row.find("th")
        value_cell = row.find("td")
        if value_cell is None:
            continue

        field_name = _normalize_inline_text(header_cell.get_text(" ", strip=True)) if header_cell else ""
        field_value = _extract_text_value(value_cell)
        if not field_value:
            continue

        if field_name:
            section_lines.append(f"| {field_name} | {field_value} |")
            last_field_name = field_name
            last_field_index = len(section_lines) - 1
            continue

        if last_field_name is not None and last_field_index is not None:
            merged_value = section_lines[last_field_index].rsplit("|", 2)[1].strip()
            section_lines[last_field_index] = f"| {last_field_name} | {merged_value}; {field_value} |"

    section_lines.append("")
    logger.debug("[模块] 基本信息字段数量: {count}", count=max(len(section_lines) - 4, 0))
    return section_lines


def _build_core_sections(product_container: Tag) -> list[str]:
    description_block = _find_block_by_heading(product_container, CORE_SECTION_DESCRIPTION)
    packaging_block = _find_block_by_heading(product_container, CORE_SECTION_PACKAGING)

    section_lines: list[str] = []

    if description_block is not None:
        section_lines.extend(_render_description_section(description_block))

    if packaging_block is not None:
        section_lines.extend(_render_packaging_section(packaging_block))

    return section_lines


def _build_image_section(product_container: Tag) -> list[str]:
    image_urls = _extract_image_urls(product_container)
    section_lines = ["## 图片链接", ""]

    if not image_urls:
        section_lines.append("- 无")
        section_lines.append("")
        logger.debug("[模块] 未提取到图片链接")
        return section_lines

    for index, image_url in enumerate(image_urls, start=1):
        label = "主图" if index == 1 else f"附图{index - 1}"
        section_lines.append(f"- {label}: {image_url}")

    section_lines.append("")
    logger.debug("[模块] 提取到图片链接数量: {count}", count=len(image_urls))
    return section_lines


def _build_other_info_section(product_container: Tag) -> list[str]:
    other_blocks: list[Tag] = []
    for block in product_container.select(".product_details_block"):
        heading = _extract_block_heading(block)
        if heading in {CORE_SECTION_DESCRIPTION, CORE_SECTION_PACKAGING}:
            continue
        if heading:
            other_blocks.append(block)

    if not other_blocks:
        logger.debug("[模块] 未发现需要放入“其他信息”的内容块")
        return []

    section_lines = ["## 其他信息", ""]
    for block in other_blocks:
        heading = _extract_block_heading(block)
        if heading is None:
            continue

        section_lines.append(f"### {heading}")
        section_lines.append("")
        rendered_body = _render_generic_block_body(block)
        if rendered_body:
            section_lines.extend(rendered_body)
        else:
            section_lines.append("无")
            section_lines.append("")

    logger.debug("[模块] 其他信息子章节数量: {count}", count=len(other_blocks))
    return section_lines


def _find_block_by_heading(product_container: Tag, heading_text: str) -> Tag | None:
    for block in product_container.select(".product_details_block"):
        if _extract_block_heading(block) == heading_text:
            return block
    return None


def _extract_block_heading(block: Tag) -> str | None:
    heading_node = block.select_one(".product_details_heading")
    if heading_node is None:
        return None
    heading_text = _normalize_inline_text(heading_node.get_text(" ", strip=True))
    return heading_text or None


def _render_description_section(block: Tag) -> list[str]:
    content_node = block.select_one(".Product_section_content")
    lines = [f"## {CORE_SECTION_DESCRIPTION}", ""]
    if content_node is None:
        lines.append("无")
        lines.append("")
        return lines

    paragraphs = _extract_paragraphs(content_node)
    if not paragraphs:
        lines.append("无")
        lines.append("")
        return lines

    for paragraph in paragraphs:
        lines.append(paragraph)
        lines.append("")

    logger.debug("[模块] 产品描述段落数量: {count}", count=len(paragraphs))
    return lines


def _render_packaging_section(block: Tag) -> list[str]:
    content_node = block.select_one(".Product_section_content")
    lines = [f"## {CORE_SECTION_PACKAGING}", ""]
    if content_node is None:
        lines.append("无")
        lines.append("")
        return lines

    tables = content_node.find_all("table", recursive=False) or content_node.find_all("table")
    if not tables:
        paragraphs = _extract_paragraphs(content_node)
        if paragraphs:
            lines.extend(_paragraphs_to_lines(paragraphs))
        else:
            lines.append("无")
            lines.append("")
        return lines

    for table in tables:
        markdown_table = _render_packaging_table(table)
        if markdown_table:
            lines.extend(markdown_table)

    return lines


def _render_generic_block_body(block: Tag) -> list[str]:
    content_node = block.select_one(".Product_section_content")
    if content_node is None:
        return []

    lines: list[str] = []
    direct_children = [child for child in content_node.children if isinstance(child, Tag)]

    if not direct_children:
        return _paragraphs_to_lines(_extract_paragraphs(content_node))

    for child in direct_children:
        child_classes = set(child.get("class", []))
        if "sub_header" in child_classes:
            sub_heading = _normalize_inline_text(child.get_text(" ", strip=True))
            if sub_heading:
                lines.append(f"#### {sub_heading}")
                lines.append("")
            continue

        if child.name == "table":
            rendered_table = _render_generic_table(child)
            if rendered_table:
                lines.extend(rendered_table)
            continue

        if child.name in {"p", "div"}:
            paragraphs = _extract_paragraphs(child)
            if paragraphs:
                lines.extend(_paragraphs_to_lines(paragraphs))

    return lines


def _render_packaging_table(table: Tag) -> list[str]:
    rows = _extract_table_rows(table)
    if len(rows) < 2:
        return []

    header_row = rows[0]
    column_headers = [cell for cell in header_row[1:] if cell]
    if not column_headers:
        column_headers = [f"列{index}" for index in range(1, len(header_row))]

    lines = [f"| 字段 | {' | '.join(column_headers)} |"]
    separator_cells = ["---"] * (len(column_headers) + 1)
    lines.append(f"| {' | '.join(separator_cells)} |")

    for row in rows[1:]:
        if not row:
            continue
        field_name = row[0] if row[0] else "未命名字段"
        values = row[1 : len(column_headers) + 1]
        values.extend([""] * (len(column_headers) - len(values)))
        lines.append(f"| {field_name} | {' | '.join(values)} |")

    lines.append("")
    logger.debug("[模块] 已渲染一张包装信息表，列数: {count}", count=len(column_headers) + 1)
    return lines


def _render_generic_table(table: Tag) -> list[str]:
    rows = _extract_table_rows(table)
    if not rows:
        return []

    if len(rows) == 1:
        return [rows[0][0], ""]

    header_row = rows[0]
    lines = [f"| {' | '.join(header_row)} |"]
    lines.append(f"| {' | '.join(['---'] * len(header_row))} |")

    for row in rows[1:]:
        padded_row = row + ([""] * (len(header_row) - len(row)))
        lines.append(f"| {' | '.join(padded_row[: len(header_row)])} |")

    lines.append("")
    return lines


def _extract_table_rows(table: Tag) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.find_all("tr", recursive=False):
        cells = [_extract_text_value(cell) for cell in row.find_all(["th", "td"], recursive=False)]
        while cells and not cells[-1]:
            cells.pop()
        if any(cells):
            rows.append(cells)
    return rows


def _extract_image_urls(product_container: Tag) -> list[str]:
    urls: list[str] = []

    for image in product_container.select(".Product_images img, #product_sub_image img"):
        for attribute_name in ("data-full-url", "data-large-url", "src"):
            candidate = image.get(attribute_name)
            if candidate and candidate not in urls:
                urls.append(candidate)
                break

    return urls


def _extract_paragraphs(container: Tag) -> list[str]:
    paragraphs: list[str] = []
    for paragraph_node in container.find_all("p", recursive=False):
        paragraphs.extend(_split_paragraph(paragraph_node.get_text("\n", strip=True)))

    if paragraphs:
        return paragraphs

    raw_text = container.get_text("\n", strip=True)
    return _split_paragraph(raw_text)


def _split_paragraph(text: str) -> list[str]:
    cleaned_text = _normalize_multiline_text(text)
    if not cleaned_text:
        return []

    segments = [
        segment.strip()
        for segment in re.split(r"\n\s*\n+", cleaned_text)
        if segment.strip()
    ]
    return segments or [cleaned_text]


def _paragraphs_to_lines(paragraphs: Iterable[str]) -> list[str]:
    lines: list[str] = []
    for paragraph in paragraphs:
        lines.append(paragraph)
        lines.append("")
    return lines


def _extract_text_value(node: Tag) -> str:
    return _normalize_inline_text(node.get_text(" ", strip=True))


def _normalize_inline_text(text: str) -> str:
    normalized = text.replace("\xa0", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalize_multiline_text(text: str) -> str:
    normalized = text.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]

    compact_lines: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank:
                compact_lines.append("")
            previous_blank = True
            continue

        compact_lines.append(line)
        previous_blank = False

    return "\n".join(compact_lines).strip()

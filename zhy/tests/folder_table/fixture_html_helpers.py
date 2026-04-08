import html
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = PROJECT_ROOT / "zhy" / "data" / "tmp"


def load_html_fixture(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


def _extract_main_table_section(html_text: str) -> str:
    start = html_text.find('<table class="htCore">')
    if start < 0:
        raise ValueError("failed to locate main htCore table in html fixture")

    end = html_text.find("</table>", start)
    if end < 0:
        raise ValueError("failed to locate main table closing tag in html fixture")

    return html_text[start : end + len("</table>")]


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(text).split())


def extract_fixture_header_titles(html_text: str) -> list[str]:
    table_section = _extract_main_table_section(html_text)
    raw_titles = re.findall(r'<span[^>]+title="([^"]+)"[^>]*>', table_section, flags=re.S)

    cleaned_titles: list[str] = []
    for raw_title in raw_titles:
        title = " ".join(html.unescape(raw_title).split())
        if not title:
            continue
        cleaned_titles.append(title)
        if len(cleaned_titles) == 6:
            break

    return cleaned_titles


def extract_visible_row_indexes(html_text: str) -> list[int]:
    table_section = _extract_main_table_section(html_text)
    row_indexes = {int(value) for value in re.findall(r'data-row="(\d+)"', table_section)}
    return sorted(row_indexes)


def extract_row_cell_texts(html_text: str, row_index: int) -> list[str]:
    table_section = _extract_main_table_section(html_text)
    for candidate in re.finditer(r"<tr>.*?</tr>", table_section, flags=re.S):
        row_html = candidate.group(0)
        if f'data-row="{row_index}"' not in row_html:
            continue

        td_fragments = re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, flags=re.S)
        return [_strip_tags(fragment) for fragment in td_fragments]

    raise ValueError(f"failed to locate row {row_index} in html fixture")

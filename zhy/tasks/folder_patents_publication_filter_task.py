import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_INPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "publication_numbers"
DEFAULT_FIELD_LABEL_MAP_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "8.json"
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2026-04-08"

PUBLICATION_NUMBER_FIELD_KEYS = (
    "PN",
    "PCT_PN",
    "publication_number",
    "publicationNo",
    "publication_no",
)

PUBLICATION_NUMBER_LABEL_KEYWORDS = (
    "公开(公告)号",
    "公开号",
    "公告号",
    "公开号",
)

PRIMARY_DATE_FIELD_KEYS = (
    "PBDT",
    "F_PBD",
    "publication_date",
    "publish_date",
    "date",
)

PRIMARY_DATE_LABEL_KEYWORDS = (
    "公开(公告)日",
    "公开(公告)日期",
    "公开日期",
    "公告日期",
    "首次公开日",
)

DATE_LIKE_LABEL_KEYWORDS = (
    "日期",
    "时间",
    "日",
)

DATE_PATTERNS = (
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
    re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})"),
    re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
    re.compile(r"(\d{4})(\d{2})(\d{2})"),
)


@dataclass(frozen=True)
class FilteredPatentRecord:
    space_id: str
    folder_id: str
    page_number: int
    publication_number: str
    date_field_name: str
    date_field_label: str
    date_value: str
    parsed_date: str
    source_file: str


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parse patents API output files, filter patents by date range, "
            "and write publication numbers to a JSON file."
        )
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--field-label-map", type=Path, default=DEFAULT_FIELD_LABEL_MAP_PATH)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    return parser


def load_json_any_utf(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(normalize_text(item) for item in value if normalize_text(item))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return " ".join(str(value).replace("\n", " ").split())


def normalize_key(value: str) -> str:
    return "".join(normalize_text(value).lower().split())


def parse_date_text(date_text: str) -> date:
    parsed = parse_date_like_value(date_text)
    if parsed is None:
        raise ValueError(f"invalid date value: {date_text}")
    return parsed


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date >= end_date:
        raise ValueError("start_date must be earlier than end_date")


def parse_date_like_value(value) -> date | None:
    cleaned = normalize_text(value)
    if not cleaned:
        return None

    for pattern in DATE_PATTERNS:
        match = pattern.search(cleaned)
        if match is None:
            continue
        try:
            year, month, day = (int(part) for part in match.groups())
            return date(year, month, day)
        except ValueError:
            continue
    return None


def load_field_label_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = load_json_any_utf(path)
    if not isinstance(payload, dict):
        return {}
    return {str(key): normalize_text(value) for key, value in payload.items()}


def build_default_output_path(output_dir: Path, start_date_text: str, end_date_text: str) -> Path:
    return output_dir / f"publication_numbers_{start_date_text}_{end_date_text}.json"


def build_plain_text_output_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_plain.txt")


def extract_space_and_folder_from_dir(folder_dir: Path) -> tuple[str, str]:
    name = folder_dir.name
    if "_" in name:
        space_id, folder_id = name.split("_", 1)
        return space_id, folder_id
    return "", name


def list_page_json_files(input_root: Path) -> list[Path]:
    return sorted(
        path
        for path in input_root.rglob("page_*.json")
        if path.is_file()
    )


def extract_patent_rows(page_payload: dict) -> list[dict]:
    data = page_payload.get("data")
    if not isinstance(data, dict):
        return []
    patents_data = data.get("patents_data")
    if not isinstance(patents_data, list):
        return []
    return [item for item in patents_data if isinstance(item, dict)]


def find_publication_number(row: dict, field_label_map: dict[str, str]) -> tuple[str, str, str] | None:
    for key in PUBLICATION_NUMBER_FIELD_KEYS:
        value = normalize_text(row.get(key))
        if value:
            label = field_label_map.get(key, "")
            return key, label, value

    for key, raw_value in row.items():
        label = field_label_map.get(str(key), "")
        key_text = normalize_text(key)
        label_text = normalize_text(label)
        value = normalize_text(raw_value)
        if not value:
            continue
        if any(keyword in key_text for keyword in PUBLICATION_NUMBER_LABEL_KEYWORDS):
            return str(key), label_text, value
        if any(keyword in label_text for keyword in PUBLICATION_NUMBER_LABEL_KEYWORDS):
            return str(key), label_text, value

    return None


def find_date_candidate(row: dict, field_label_map: dict[str, str]) -> tuple[str, str, str, date] | None:
    for key in PRIMARY_DATE_FIELD_KEYS:
        raw_value = row.get(key)
        parsed = parse_date_like_value(raw_value)
        if parsed is None:
            continue
        return key, field_label_map.get(key, ""), normalize_text(raw_value), parsed

    for key, raw_value in row.items():
        key_text = normalize_text(key)
        label_text = field_label_map.get(str(key), "")
        parsed = parse_date_like_value(raw_value)
        if parsed is None:
            continue
        if any(keyword in key_text for keyword in PRIMARY_DATE_LABEL_KEYWORDS):
            return str(key), label_text, normalize_text(raw_value), parsed
        if any(keyword in label_text for keyword in PRIMARY_DATE_LABEL_KEYWORDS):
            return str(key), label_text, normalize_text(raw_value), parsed

    for key, raw_value in row.items():
        key_text = normalize_text(key)
        label_text = field_label_map.get(str(key), "")
        parsed = parse_date_like_value(raw_value)
        if parsed is None:
            continue
        if any(keyword in key_text for keyword in DATE_LIKE_LABEL_KEYWORDS):
            return str(key), label_text, normalize_text(raw_value), parsed
        if any(keyword in label_text for keyword in DATE_LIKE_LABEL_KEYWORDS):
            return str(key), label_text, normalize_text(raw_value), parsed

    for key, raw_value in row.items():
        parsed = parse_date_like_value(raw_value)
        if parsed is None:
            continue
        return str(key), field_label_map.get(str(key), ""), normalize_text(raw_value), parsed

    return None


def select_publication_numbers_in_date_range(
    input_root: Path,
    field_label_map: dict[str, str],
    start_date: date,
    end_date: date,
) -> list[FilteredPatentRecord]:
    validate_date_range(start_date, end_date)
    matched_records: list[FilteredPatentRecord] = []

    for page_path in list_page_json_files(input_root):
        folder_dir = page_path.parent
        space_id, folder_id = extract_space_and_folder_from_dir(folder_dir)
        try:
            page_payload = load_json_any_utf(page_path)
        except Exception as exc:
            logger.warning(
                "[folder_patents_publication_filter_task] skip unreadable file {}: {}",
                page_path,
                exc,
            )
            continue

        rows = extract_patent_rows(page_payload)
        page_match = re.search(r"page_(\d+)\.json$", page_path.name)
        page_number = int(page_match.group(1)) if page_match else 0

        for row in rows:
            publication_field = find_publication_number(row, field_label_map)
            if publication_field is None:
                continue

            date_field = find_date_candidate(row, field_label_map)
            if date_field is None:
                continue

            parsed_date = date_field[3]
            if parsed_date < start_date or parsed_date > end_date:
                continue

            matched_records.append(
                FilteredPatentRecord(
                    space_id=space_id,
                    folder_id=folder_id,
                    page_number=page_number,
                    publication_number=publication_field[2],
                    date_field_name=date_field[0],
                    date_field_label=normalize_text(date_field[1]),
                    date_value=date_field[2],
                    parsed_date=parsed_date.isoformat(),
                    source_file=str(page_path),
                )
            )

    return dedupe_publication_numbers(matched_records)


def dedupe_publication_numbers(records: list[FilteredPatentRecord]) -> list[FilteredPatentRecord]:
    deduped: list[FilteredPatentRecord] = []
    seen: set[str] = set()

    for record in records:
        publication_number = normalize_text(record.publication_number)
        if not publication_number or publication_number in seen:
            continue
        seen.add(publication_number)
        deduped.append(record)
    return deduped


def write_filtered_publication_numbers(
    output_path: Path,
    matched_records: list[FilteredPatentRecord],
    start_date: date,
    end_date: date,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped_records = dedupe_publication_numbers(matched_records)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "publication_number_count": len(deduped_records),
        "publication_numbers": [record.publication_number for record in deduped_records],
        "records": [
            {
                "space_id": record.space_id,
                "folder_id": record.folder_id,
                "page_number": record.page_number,
                "publication_number": record.publication_number,
                "date_field_name": record.date_field_name,
                "date_field_label": record.date_field_label,
                "date_value": record.date_value,
                "parsed_date": record.parsed_date,
                "source_file": record.source_file,
            }
            for record in deduped_records
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_plain_publication_number_list(
    output_path: Path,
    matched_records: list[FilteredPatentRecord],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped_records = dedupe_publication_numbers(matched_records)
    lines = [f"{record.publication_number}," for record in deduped_records]
    content = "\n".join(lines)
    if content:
        content += "\n"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    start_date = parse_date_text(args.start_date)
    end_date = parse_date_text(args.end_date)
    validate_date_range(start_date, end_date)

    field_label_map = load_field_label_map(args.field_label_map)
    output_path = args.output_file or build_default_output_path(args.output_dir, args.start_date, args.end_date)

    matched_records = select_publication_numbers_in_date_range(
        input_root=args.input_root,
        field_label_map=field_label_map,
        start_date=start_date,
        end_date=end_date,
    )
    written_path = write_filtered_publication_numbers(
        output_path=output_path,
        matched_records=matched_records,
        start_date=start_date,
        end_date=end_date,
    )
    plain_text_output_path = build_plain_text_output_path(output_path)
    plain_text_written_path = write_plain_publication_number_list(
        output_path=plain_text_output_path,
        matched_records=matched_records,
    )
    logger.info(
        "[folder_patents_publication_filter_task] finished: matched_publication_numbers={} json_output={} plain_text_output={}",
        len(matched_records),
        written_path,
        plain_text_written_path,
    )


if __name__ == "__main__":
    main()

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_HYBRID_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"
DEFAULT_PUBLICATION_FILE = (
    PROJECT_ROOT
    / "zhy"
    / "data"
    / "output"
    / "publication_numbers"
    / "publication_numbers_2025-04-08_2026-04-08_plain.txt"
)
DEFAULT_TASK_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "output_integrity_check"
REQUIRED_FIELDS = ("PBD", "APD", "PN", "APN")


@dataclass
class FieldCheckResult:
    total_json_files: int
    total_rows: int
    missing_rows: list[dict[str, object]]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check output integrity for hybrid pages and publication number duplicates.")
    parser.add_argument("--hybrid-output-dir", type=Path, default=DEFAULT_HYBRID_OUTPUT_DIR)
    parser.add_argument("--publication-file", type=Path, default=DEFAULT_PUBLICATION_FILE)
    parser.add_argument("--task-output-dir", type=Path, default=DEFAULT_TASK_OUTPUT_DIR)
    parser.add_argument("--duplicate-output-file", type=Path)
    parser.add_argument("--missing-fields-output-file", type=Path)
    return parser


def iter_page_json_files(hybrid_output_dir: Path) -> list[Path]:
    return sorted(path for path in hybrid_output_dir.rglob("page_*.json") if path.is_file())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_required_fields_on_rows(hybrid_output_dir: Path) -> FieldCheckResult:
    page_files = iter_page_json_files(hybrid_output_dir)
    missing_rows: list[dict[str, object]] = []
    total_rows = 0

    for page_file in page_files:
        payload = load_json(page_file)
        rows = payload.get("data", {}).get("patents_data", [])
        if not isinstance(rows, list):
            missing_rows.append(
                {
                    "file": str(page_file),
                    "row_index": -1,
                    "missing_fields": list(REQUIRED_FIELDS),
                    "reason": "data.patents_data is not a list",
                }
            )
            continue

        for index, row in enumerate(rows):
            total_rows += 1
            if not isinstance(row, dict):
                missing_rows.append(
                    {
                        "file": str(page_file),
                        "row_index": index,
                        "missing_fields": list(REQUIRED_FIELDS),
                        "reason": "row is not a dict",
                    }
                )
                continue

            missing_fields = [field for field in REQUIRED_FIELDS if field not in row]
            if missing_fields:
                missing_rows.append(
                    {
                        "file": str(page_file),
                        "row_index": index,
                        "missing_fields": missing_fields,
                    }
                )

    return FieldCheckResult(
        total_json_files=len(page_files),
        total_rows=total_rows,
        missing_rows=missing_rows,
    )


def read_publication_numbers(publication_file: Path) -> list[str]:
    values: list[str] = []
    for raw_line in publication_file.read_text(encoding="utf-8").splitlines():
        value = raw_line.strip().rstrip(",")
        if value:
            values.append(value)
    return values


def find_duplicates(values: list[str]) -> dict[str, int]:
    counts = Counter(values)
    return {value: count for value, count in counts.items() if count > 1}


def build_duplicate_output_path(publication_file: Path) -> Path:
    stem = publication_file.stem
    return publication_file.with_name(f"{stem}_duplicates.txt")


def build_duplicate_output_path_in_task_dir(task_output_dir: Path, publication_file: Path) -> Path:
    stem = publication_file.stem
    return task_output_dir / f"{stem}_duplicates.txt"


def build_missing_fields_output_path(task_output_dir: Path) -> Path:
    return task_output_dir / "missing_required_fields.json"


def write_duplicates(duplicate_output_file: Path, duplicates: dict[str, int]) -> None:
    duplicate_output_file.parent.mkdir(parents=True, exist_ok=True)
    if not duplicates:
        duplicate_output_file.write_text("", encoding="utf-8")
        return

    lines = [f"{value}\t{count}" for value, count in sorted(duplicates.items())]
    duplicate_output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_missing_fields(missing_fields_output_file: Path, field_result: FieldCheckResult) -> None:
    missing_fields_output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "required_fields": list(REQUIRED_FIELDS),
        "total_json_files": field_result.total_json_files,
        "total_rows": field_result.total_rows,
        "missing_row_count": len(field_result.missing_rows),
        "missing_rows": field_result.missing_rows,
    }
    missing_fields_output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    field_result = check_required_fields_on_rows(args.hybrid_output_dir)
    has_missing_fields = len(field_result.missing_rows) > 0

    publication_values = read_publication_numbers(args.publication_file)
    duplicates = find_duplicates(publication_values)
    has_duplicates = len(duplicates) > 0

    args.task_output_dir.mkdir(parents=True, exist_ok=True)

    duplicate_output_file = args.duplicate_output_file or build_duplicate_output_path_in_task_dir(
        args.task_output_dir,
        args.publication_file,
    )
    missing_fields_output_file = args.missing_fields_output_file or build_missing_fields_output_path(args.task_output_dir)

    write_duplicates(duplicate_output_file, duplicates)
    write_missing_fields(missing_fields_output_file, field_result)

    logger.info(
        "[output_integrity_check] hybrid_rows_have_required_fields={} total_json_files={} total_rows={} missing_rows={}",
        "否" if has_missing_fields else "是",
        field_result.total_json_files,
        field_result.total_rows,
        len(field_result.missing_rows),
    )
    logger.info(
        "[output_integrity_check] publication_file_has_duplicates={} total_values={} duplicate_value_count={} duplicate_output={} missing_fields_output={}",
        "是" if has_duplicates else "否",
        len(publication_values),
        len(duplicates),
        duplicate_output_file,
        missing_fields_output_file,
    )

    print(f"字段完整性(都含PBD/APD/PN/APN): {'否' if has_missing_fields else '是'}")
    print(f"publication number是否有重复: {'是' if has_duplicates else '否'}")
    print(f"重复字段输出文件: {duplicate_output_file}")
    print(f"缺失字段明细输出文件: {missing_fields_output_file}")


if __name__ == "__main__":
    main()
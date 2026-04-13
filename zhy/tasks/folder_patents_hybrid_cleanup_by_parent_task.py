import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_INPUT_JSON = PROJECT_ROOT / "zhy" / "data" / "tmp" / "mid10.json"
DEFAULT_HYBRID_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_hybrid"
DEFAULT_TASK_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "cleanup_by_parent_id"
DEFAULT_TARGET_PARENT_ID = "8614f137547f4e46b8557ae8d3b1e1f5"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete folder_patents_hybrid directories whose source records have parent_id != target parent id."
    )
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT_JSON)
    parser.add_argument("--hybrid-output-dir", type=Path, default=DEFAULT_HYBRID_OUTPUT_DIR)
    parser.add_argument("--task-output-dir", type=Path, default=DEFAULT_TASK_OUTPUT_DIR)
    parser.add_argument("--target-parent-id", default=DEFAULT_TARGET_PARENT_ID)
    parser.add_argument("--dry-run", action="store_true", help="Only generate report, do not delete directories.")
    return parser


def load_records(input_json: Path) -> list[dict[str, object]]:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ValueError("mid10.json format error: payload.data is not a list")
    return [row for row in data if isinstance(row, dict)]


def select_records_to_remove(records: list[dict[str, object]], target_parent_id: str) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for row in records:
        parent_id = str(row.get("parent_id", ""))
        if parent_id != target_parent_id:
            selected.append(row)
    return selected


def find_candidate_directories(hybrid_output_dir: Path, space_id: str, folder_id: str) -> list[Path]:
    exact_path = hybrid_output_dir / f"{space_id}_{folder_id}"
    if exact_path.is_dir():
        return [exact_path]

    # Fallback pattern in case historical data uses a different space prefix.
    matches = sorted(path for path in hybrid_output_dir.glob(f"*_{folder_id}") if path.is_dir())
    return matches


def build_row_summary(row: dict[str, object]) -> dict[str, str]:
    return {
        "space_id": str(row.get("space_id", "")),
        "folder_id": str(row.get("folder_id", "")),
        "parent_id": str(row.get("parent_id", "")),
        "folder_name": str(row.get("folder_name", "")),
    }


def build_name_output_path(task_output_dir: Path) -> Path:
    return task_output_dir / "records_to_remove_names.txt"


def write_records_to_remove_names(name_output_path: Path, rows: list[dict[str, object]]) -> None:
    names: list[str] = []
    for row in rows:
        folder_name = str(row.get("folder_name", "")).strip()
        folder_id = str(row.get("folder_id", "")).strip()
        if folder_name:
            names.append(f"{folder_name}\t{folder_id}")
        else:
            names.append(f"(空名称)\t{folder_id}")

    text = "\n".join(names)
    if text:
        text += "\n"
    name_output_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    records = load_records(args.input_json)
    to_remove_rows = select_records_to_remove(records, args.target_parent_id)

    matched_directories: list[str] = []
    deleted_directories: list[str] = []
    missing_rows: list[dict[str, str]] = []

    for row in to_remove_rows:
        space_id = str(row.get("space_id", ""))
        folder_id = str(row.get("folder_id", ""))
        if not space_id or not folder_id:
            missing_rows.append(build_row_summary(row))
            continue

        candidates = find_candidate_directories(args.hybrid_output_dir, space_id, folder_id)
        if not candidates:
            missing_rows.append(build_row_summary(row))
            continue

        for candidate in candidates:
            matched_directories.append(str(candidate))
            if not args.dry_run:
                shutil.rmtree(candidate)
                deleted_directories.append(str(candidate))

    args.task_output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.task_output_dir / "cleanup_report.json"
    name_output_path = build_name_output_path(args.task_output_dir)
    write_records_to_remove_names(name_output_path, to_remove_rows)

    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "input_json": str(args.input_json),
        "hybrid_output_dir": str(args.hybrid_output_dir),
        "target_parent_id": args.target_parent_id,
        "dry_run": args.dry_run,
        "records_total": len(records),
        "records_to_remove": len(to_remove_rows),
        "matched_directory_count": len(matched_directories),
        "deleted_directory_count": len(deleted_directories),
        "missing_record_count": len(missing_rows),
        "records_to_remove_name_output": str(name_output_path),
        "rows_to_remove": [build_row_summary(row) for row in to_remove_rows],
        "matched_directories": matched_directories,
        "deleted_directories": deleted_directories,
        "missing_rows": missing_rows,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    logger.info(
        "[cleanup_by_parent] dry_run={} records_total={} records_to_remove={} matched={} deleted={} missing={} report={} names_output={}",
        args.dry_run,
        len(records),
        len(to_remove_rows),
        len(matched_directories),
        len(deleted_directories),
        len(missing_rows),
        report_path,
        name_output_path,
    )

    print(f"待删除记录数: {len(to_remove_rows)}")
    print(f"匹配目录数: {len(matched_directories)}")
    print(f"实际删除目录数: {len(deleted_directories)}")
    print(f"未匹配记录数: {len(missing_rows)}")
    print(f"报告文件: {report_path}")
    print(f"待删除记录名称文件: {name_output_path}")


if __name__ == "__main__":
    main()
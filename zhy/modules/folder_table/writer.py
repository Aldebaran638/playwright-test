import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from zhy.modules.folder_table.models import FolderTarget, TableRowRecord, TableSchema


def get_folder_output_dir(output_root_dir: Path, target: FolderTarget) -> Path:
    output_dir = output_root_dir / target.space_id / target.folder_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_schema(output_dir: Path, schema: TableSchema) -> Path:
    schema_path = output_dir / "schema.json"
    payload = {
        "columns": schema.columns,
        "column_count": schema.column_count,
    }
    schema_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return schema_path


def append_rows(output_dir: Path, rows: list[TableRowRecord]) -> Path:
    rows_path = output_dir / "rows.jsonl"
    with rows_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
    return rows_path


def write_meta(output_dir: Path, meta: dict[str, Any]) -> Path:
    meta_path = output_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta_path

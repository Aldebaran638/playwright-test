import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from zhy.modules.folder_table.models import FolderTarget, TableRowRecord, TableSchema


def get_folder_output_dir(output_root_dir: Path, target: FolderTarget) -> Path:
    # 每个 folderId 使用独立输出目录，防止不同字段结构混写到同一文件。
    output_dir = output_root_dir / target.space_id / target.folder_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_schema(output_dir: Path, schema: TableSchema) -> Path:
    # 单独保存当前文件夹的字段结构，方便后续校验和复用。
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
    # 逐行追加写入，避免覆盖已有抓取结果。
    rows_path = output_dir / "rows.jsonl"
    with rows_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
    return rows_path


def write_meta(output_dir: Path, meta: dict[str, Any]) -> Path:
    # 保存抓取统计和文件夹元信息，便于后续续跑或排错。
    meta_path = output_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta_path

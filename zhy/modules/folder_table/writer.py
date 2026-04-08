import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from zhy.modules.folder_table.models import FolderTarget, TableRowRecord, TableSchema


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_folder_output_dir(output_root_dir: Path, target: FolderTarget) -> Path:
    # 每个 folderId 使用独立输出目录，防止不同字段结构混写到同一文件。
    output_dir = output_root_dir / target.space_id / target.folder_id
    return ensure_output_dir(output_dir)


def write_schema(output_dir: Path, schema: TableSchema) -> Path:
    # 单独保存当前文件夹的字段结构，方便后续校验和复用。
    ensure_output_dir(output_dir)
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
    ensure_output_dir(output_dir)
    rows_path = output_dir / "rows.jsonl"
    with rows_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
    return rows_path


def append_failure(output_dir: Path, payload: dict[str, Any]) -> Path:
    # 逐条追加失败记录，便于离线排查为什么没有产出数据。
    ensure_output_dir(output_dir)
    failures_path = output_dir / "failures.jsonl"
    with failures_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return failures_path


def append_debug(output_dir: Path, payload: dict[str, Any]) -> Path:
    # 逐页记录调试快照，保留线上实际命中的表头、行数和样例数据。
    ensure_output_dir(output_dir)
    debug_path = output_dir / "debug.jsonl"
    with debug_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return debug_path


def write_meta(output_dir: Path, meta: dict[str, Any]) -> Path:
    # 保存抓取统计和文件夹元信息，便于后续续跑或排错。
    ensure_output_dir(output_dir)
    meta_path = output_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta_path

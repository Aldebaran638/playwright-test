import json
from pathlib import Path

from zhy.modules.folder_table.models import FolderTarget, TableSchema
from zhy.modules.folder_table.writer import ensure_output_dir
from zhy.modules.folder_table_probe.models import PageProbeResult


# 简介：定位当前文件夹的统一输出目录。
# 参数：
# - output_root_dir: 探测输出根目录。
# - target: 当前文件夹目标。
# 返回值：
# - 当前文件夹的输出目录路径。
# 逻辑：
# - 所有页码都写到同一个 folder 目录下，不再为每个 page 单独建目录。
def get_folder_probe_output_dir(output_root_dir: Path, target: FolderTarget) -> Path:
    return ensure_output_dir(output_root_dir / target.space_id / target.folder_id)


def _write_schema(output_dir: Path, schema: TableSchema) -> Path:
    schema_path = output_dir / "schema.json"
    schema_path.write_text(
        json.dumps(
            {"columns": schema.columns, "column_count": schema.column_count},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return schema_path


def _write_rows(output_dir: Path, page_results: list[PageProbeResult]) -> tuple[Path, int]:
    rows_path = output_dir / "rows.jsonl"
    next_folder_row_number = 1
    written_count = 0

    with rows_path.open("w", encoding="utf-8") as handle:
        for page_result in sorted(page_results, key=lambda item: item.page_number):
            if not page_result.success:
                continue
            for page_row_number, row in enumerate(page_result.rows, start=1):
                handle.write(
                    json.dumps(
                        {
                            "folder_row_number": next_folder_row_number,
                            "page_number": row.page_number,
                            "page_row_number": page_row_number,
                            "row_key": row.row_key,
                            "folder_id": row.folder_id,
                            "data": row.data,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                next_folder_row_number += 1
                written_count += 1

    return rows_path, written_count


def _write_failures(output_dir: Path, page_results: list[PageProbeResult]) -> Path:
    failures_path = output_dir / "failures.jsonl"
    with failures_path.open("w", encoding="utf-8") as handle:
        for page_result in sorted(page_results, key=lambda item: item.page_number):
            if page_result.success:
                continue
            handle.write(
                json.dumps(
                    {
                        "page_number": page_result.page_number,
                        "error_message": page_result.error_message,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return failures_path


# 简介：把单个文件夹的多页探测结果聚合写入同一个目录。
# 参数：
# - output_root_dir: 探测输出根目录。
# - target: 当前文件夹目标。
# - page_results: 当前文件夹的全部页探测结果。
# 返回值：
# - 返回 (output_dir, appended_count, schema)，分别表示输出目录、本次追加行数和最终字段结构。
# 逻辑：
# - 先写 schema，再把所有成功页按页码排序后重写进同一个 rows.jsonl，并同步更新 meta 和 failures。
def write_folder_probe_output(
    output_root_dir: Path,
    target: FolderTarget,
    page_results: list[PageProbeResult],
) -> tuple[Path, int, TableSchema | None]:
    output_dir = get_folder_probe_output_dir(output_root_dir, target)
    successful_results = [result for result in page_results if result.success]
    schema = next((result.schema for result in successful_results if result.schema is not None), None)

    schema_path: str | None = None
    if schema is not None:
        schema_path = str(_write_schema(output_dir, schema))

    rows_path, written_count = _write_rows(output_dir, page_results)
    failures_path = _write_failures(output_dir, page_results)

    meta_path = output_dir / "meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "space_id": target.space_id,
                "folder_id": target.folder_id,
                "successful_pages": [result.page_number for result in successful_results],
                "failed_pages": [result.page_number for result in page_results if not result.success],
                "written_rows": written_count,
                "schema_path": schema_path,
                "rows_path": str(rows_path),
                "failures_path": str(failures_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_dir, written_count, schema
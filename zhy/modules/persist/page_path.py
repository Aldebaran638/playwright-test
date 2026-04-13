from __future__ import annotations

from pathlib import Path


# 简介：构建单页文件夹专利数据的输出文件路径。
# 参数：output_root 为输出根目录；space_id 和 folder_id 为 workspace 标识；page 为页码。
# 返回值：page_XXXX.json 文件路径。
def build_patents_page_path(output_root: Path, space_id: str, folder_id: str, page: int) -> Path:
    folder_dir = output_root / f"{space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{page:04d}.json"


# 简介：构建专利抓取运行 summary 文件路径。
# 参数：output_root 为输出根目录；space_id 为 workspace 标识。
# 返回值：summary JSON 文件路径。
def build_patents_summary_path(output_root: Path, space_id: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / f"{space_id}_run_summary.json"


# 简介：构建按月专利抓取单页输出路径。
# 参数：output_root 为月度输出根目录；space_id 和 folder_id 为标识；source_page_number 为原始页码。
# 返回值：page_XXXX.json 文件路径。
def build_monthly_page_output_path(output_root: Path, space_id: str, folder_id: str, source_page_number: int) -> Path:
    folder_dir = output_root / f"{space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{source_page_number:04d}.json"


# 简介：构建月度抓取汇总文件路径。
# 参数：output_root 为输出根目录；month_text 为 YYYY-MM 格式月份。
# 返回值：汇总 JSON 文件路径。
def build_monthly_run_summary_path(output_root: Path, month_text: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    safe_month = month_text.replace("-", "_")
    return output_root / f"monthly_patents_{safe_month}_run_summary.json"


# 简介：把 enrichment 输出路径镜像自输入路径。
# 参数：output_root 为 enrichment 输出根目录；input_root 为原始数据根目录；page_file 为具体输入文件路径。
# 返回值：对应的 enrichment 输出文件路径。
def build_enrichment_page_path(output_root: Path, input_root: Path, page_file: Path) -> Path:
    relative_path = page_file.relative_to(input_root)
    output_path = output_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


# 简介：递归查找输入目录下的所有 page_*.json 文件并排序。
# 参数：input_root 为扫描根目录。
# 返回值：排序后的文件路径列表。
def iter_input_page_files(input_root: Path) -> list[Path]:
    return sorted(path for path in input_root.rglob("page_*.json") if path.is_file())


# 简介：从父目录名解析 space_id 和 folder_id。
# 参数：folder_dir 为形如 space_folder 的目录对象。
# 返回值：(space_id, folder_id) 元组；无法解析时 space_id 为空字符串。
def parse_space_folder_from_parent(folder_dir: Path) -> tuple[str, str]:
    name = folder_dir.name
    if "_" not in name:
        return "", name
    return name.split("_", 1)

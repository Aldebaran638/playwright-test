from __future__ import annotations

from pathlib import Path


def build_patents_page_path(output_root: Path, space_id: str, folder_id: str, page: int) -> Path:
    folder_dir = output_root / f"{space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{page:04d}.json"


def build_patents_summary_path(output_root: Path, space_id: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / f"{space_id}_run_summary.json"


def build_monthly_page_output_path(output_root: Path, space_id: str, folder_id: str, source_page_number: int) -> Path:
    folder_dir = output_root / f"{space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{source_page_number:04d}.json"


def build_monthly_run_summary_path(output_root: Path, month_text: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    safe_month = month_text.replace("-", "_")
    return output_root / f"monthly_patents_{safe_month}_run_summary.json"


def build_enrichment_page_path(output_root: Path, input_root: Path, page_file: Path) -> Path:
    relative_path = page_file.relative_to(input_root)
    output_path = output_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def iter_input_page_files(input_root: Path) -> list[Path]:
    return sorted(path for path in input_root.rglob("page_*.json") if path.is_file())


def iter_folder_page_files(folder_dir: Path) -> list[Path]:
    if not folder_dir.exists() or not folder_dir.is_dir():
        return []
    return sorted(path for path in folder_dir.glob("page_*.json") if path.is_file())


def has_existing_page_files(folder_dir: Path) -> bool:
    return bool(iter_folder_page_files(folder_dir))


def parse_space_folder_from_parent(folder_dir: Path) -> tuple[str, str]:
    name = folder_dir.name
    if "_" not in name:
        return "", name
    return name.split("_", 1)

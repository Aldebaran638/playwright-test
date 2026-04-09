from __future__ import annotations

import json
from pathlib import Path

from zhy.modules.folder_patents_hybrid.models import FolderAuthState


def save_json(path: Path, payload: dict) -> None:
    """写入 JSON 文件（自动创建父目录）。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json_file_any_utf(path: Path) -> dict:
    """读取 JSON 文件，兼容 utf-8 BOM。"""

    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_auth_state_if_valid(path: Path, expected_space_id: str, expected_folder_id: str) -> FolderAuthState | None:
    """读取并校验缓存鉴权状态，仅在 space_id/folder_id 匹配时返回。"""

    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    auth_state = FolderAuthState.from_json(raw)
    if auth_state.space_id != expected_space_id or auth_state.folder_id != expected_folder_id:
        return None
    if not auth_state.request_url or not auth_state.body_template:
        return None
    return auth_state


def build_output_path(output_root: Path, space_id: str, folder_id: str, page: int) -> Path:
    """构建单页输出文件路径。"""

    folder_dir = output_root / f"{space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{page:04d}.json"


def build_summary_path(output_root: Path, space_id: str) -> Path:
    """构建本次运行 summary 文件路径。"""

    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / f"{space_id}_run_summary.json"

from __future__ import annotations

import json
from pathlib import Path

from zhy.modules.common.types.folder_patents import FolderAuthState


# 简介：读取并校验缓存鉴权状态，仅在 space_id/folder_id 匹配时返回。
# 参数：path 为鉴权状态文件路径；expected_space_id 和 expected_folder_id 为期望匹配值。
# 返回值：FolderAuthState 或 None。
def load_auth_state_if_valid(path: Path, expected_space_id: str, expected_folder_id: str) -> FolderAuthState | None:
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


# 简介：读取已缓存的鉴权状态，缺失或无效时返回 None（不做 space_id/folder_id 校验）。
# 参数：path 为鉴权状态文件路径。
# 返回值：FolderAuthState 或 None。
def load_auth_state_from_file(path: Path) -> FolderAuthState | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    auth_state = FolderAuthState.from_json(payload)
    if not auth_state.authorization and not auth_state.cookie_header:
        return None
    return auth_state

from __future__ import annotations

import json
from pathlib import Path


# 简介：写入 JSON 文件，自动创建父目录。
# 参数：path 为目标文件路径；payload 为要写入的数据。
# 返回值：无。
def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# 简介：读取 JSON 文件，兼容 utf-8 BOM。
# 参数：path 为目标文件路径。
# 返回值：解析后的字典。
def load_json_file_any_utf(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))

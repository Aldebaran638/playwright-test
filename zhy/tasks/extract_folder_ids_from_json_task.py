import argparse
import json
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "zhy" / "data" / "tmp" / "mid9.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_ids"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract folder_id list from folder tree JSON.")
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def load_json_any_utf(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def extract_folder_ids(payload: dict) -> list[str]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []

    folder_ids: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        folder_id = item.get("folder_id")
        if not isinstance(folder_id, str) or not folder_id:
            continue
        if folder_id in seen:
            continue
        seen.add(folder_id)
        folder_ids.append(folder_id)
    return folder_ids


def write_outputs(output_dir: Path, folder_ids: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / "folder_ids.txt"
    json_path = output_dir / "folder_ids.json"
    pylist_path = output_dir / "folder_ids_pylist.txt"

    txt_path.write_text("\n".join(folder_ids) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(folder_ids, ensure_ascii=False, indent=2), encoding="utf-8")

    pylist_lines = ["DEFAULT_FOLDER_IDS: list[str] = ["]
    for folder_id in folder_ids:
        pylist_lines.append(f'    "{folder_id}",')
    pylist_lines.append("]")
    pylist_path.write_text("\n".join(pylist_lines) + "\n", encoding="utf-8")

    logger.info(
        "[extract_folder_ids_from_json_task] done: count={} txt={} json={} pylist={}",
        len(folder_ids),
        txt_path,
        json_path,
        pylist_path,
    )


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    payload = load_json_any_utf(args.input_file)
    folder_ids = extract_folder_ids(payload)
    write_outputs(args.output_dir, folder_ids)


if __name__ == "__main__":
    main()

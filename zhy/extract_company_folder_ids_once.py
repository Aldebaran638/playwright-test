from pathlib import Path
import json
import re


INPUT_PATH = Path("zhy/data/output/2026-01/competitor_patent_pipeline/competitor_folder_mapping_raw.json")
OUTPUT_PATH = Path("zhy/data/output/2026-01/competitor_patent_pipeline/company_folder_ids.json")


def main() -> None:
    lines = INPUT_PATH.read_text(encoding="utf-8").splitlines()
    folder_pattern = re.compile(r'"folder_id"\s*:\s*"([0-9a-f]{32})"')
    parent_pattern = re.compile(r'"parent_id"\s*:\s*"([^"]+)"')

    valid_folder_ids = {
        match.group(1)
        for line in lines
        for match in [folder_pattern.search(line)]
        if match
    }

    company_folder_ids = []
    current_folder_id = None
    for line in lines:
        folder_match = folder_pattern.search(line)
        if folder_match:
            current_folder_id = folder_match.group(1)
            continue

        parent_match = parent_pattern.search(line)
        if current_folder_id and parent_match:
            parent_id = parent_match.group(1)
            if parent_id != "-root" and parent_id in valid_folder_ids:
                company_folder_ids.append(current_folder_id)
            current_folder_id = None

    OUTPUT_PATH.write_text(
        json.dumps(company_folder_ids, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"saved {len(company_folder_ids)} company folder ids -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

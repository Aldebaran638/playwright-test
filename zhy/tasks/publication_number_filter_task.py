import argparse
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.folder_table_probe import (
    parse_filter_date,
    select_publications_in_date_range_from_output,
    write_filtered_publication_numbers,
)


DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_table_probe"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filter publication numbers from folder_table_probe output by date range.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT_DIR)
    parser.add_argument("--start-date", required=True, help="Inclusive start date, for example 2025-01-01")
    parser.add_argument("--end-date", required=True, help="Inclusive end date, for example 2026-01-01")
    parser.add_argument("--output-file", type=Path)
    return parser


def build_default_output_path(output_root_dir: Path, start_date_text: str, end_date_text: str) -> Path:
    return output_root_dir / f"publication_numbers_{start_date_text}_{end_date_text}.json"


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    start_date = parse_filter_date(args.start_date)
    end_date = parse_filter_date(args.end_date)
    output_path = args.output_file or build_default_output_path(args.output_root, args.start_date, args.end_date)

    matched_records = select_publications_in_date_range_from_output(
        output_root_dir=args.output_root,
        start_date=start_date,
        end_date=end_date,
    )
    written_path = write_filtered_publication_numbers(
        output_path=output_path,
        matched_records=matched_records,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(
        "[publication_number_filter_task] finished: matched_publication_numbers={} output={}",
        len(matched_records),
        written_path,
    )


if __name__ == "__main__":
    main()
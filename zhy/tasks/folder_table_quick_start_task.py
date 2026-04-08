import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.tasks.folder_table_collect_task import run_task


FOLDER_URLS = [
    "https://workspace.zhihuiya.com/detail/patent/table?spaceId=ccb6031b05034c7ab2c4b120c2dc3155&folderId=306f9f76aa5940a0acfc4b8a4dad8a18&page=1"
]
OUTPUT_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_tables"
COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
CONCURRENCY = 3
START_PAGE = 1
PAGE_SIZE = 100
ZOOM_RATIO = 0.8
PAGE_TIMEOUT_MS = 30000
TABLE_READY_TIMEOUT_MS = 120000
SCROLL_STEP_PIXELS = 420
SCROLL_PAUSE_SECONDS = 0.5
MAX_STABLE_SCROLL_ROUNDS = 3
RETRY_COUNT = 3
RETRY_WAIT_SECONDS = 2.0


class QuickStartArgs:
    folder_urls = FOLDER_URLS
    concurrency = CONCURRENCY
    start_page = START_PAGE
    page_size = PAGE_SIZE
    zoom_ratio = ZOOM_RATIO
    page_timeout_ms = PAGE_TIMEOUT_MS
    table_ready_timeout_ms = TABLE_READY_TIMEOUT_MS
    scroll_step_pixels = SCROLL_STEP_PIXELS
    scroll_pause_seconds = SCROLL_PAUSE_SECONDS
    max_stable_scroll_rounds = MAX_STABLE_SCROLL_ROUNDS
    retry_count = RETRY_COUNT
    retry_wait_seconds = RETRY_WAIT_SECONDS
    output_root = OUTPUT_ROOT
    cookie_path = COOKIE_PATH


def main() -> None:
    asyncio.run(run_task(QuickStartArgs()))


if __name__ == "__main__":
    main()

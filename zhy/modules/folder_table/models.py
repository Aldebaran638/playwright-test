from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FolderTarget:
    space_id: str
    folder_id: str
    base_url: str


@dataclass(frozen=True)
class TableSchema:
    columns: list[str]
    column_count: int


@dataclass(frozen=True)
class TableRowRecord:
    folder_id: str
    page_number: int
    row_key: str
    data: dict[str, str]


@dataclass(frozen=True)
class PageCollectResult:
    folder_id: str
    page_number: int
    schema: TableSchema | None
    rows: list[TableRowRecord]
    is_empty: bool


@dataclass
class FolderCollectResult:
    folder_id: str
    space_id: str
    schema: TableSchema | None
    output_dir: Path
    total_pages_collected: int
    total_rows_collected: int
    empty_page_number: int | None = None
    collected_page_numbers: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class FolderTableConfig:
    output_root_dir: Path
    concurrency: int = 3
    start_page: int = 1
    expected_page_size: int = 100
    zoom_ratio: float = 0.8
    page_timeout_ms: int = 30000
    table_ready_timeout_ms: int = 15000
    scroll_step_pixels: int = 420
    scroll_pause_seconds: float = 0.5
    max_stable_scroll_rounds: int = 3
    empty_page_wait_seconds: float = 3.0

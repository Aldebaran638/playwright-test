from dataclasses import dataclass, field
from pathlib import Path

from zhy.modules.folder_table.models import TableRowRecord, TableSchema


@dataclass(frozen=True)
class FolderTableProbeConfig:
    output_root_dir: Path
    page_numbers: list[int]
    page_concurrency: int
    page_size: int
    page_timeout_ms: int
    table_ready_timeout_ms: int
    buffer_wait_seconds: float
    scroll_step_pixels: int
    scroll_pause_seconds: float
    max_stable_scroll_rounds: int


@dataclass(frozen=True)
class PageProbeResult:
    page_number: int
    success: bool
    schema: TableSchema | None
    rows: list[TableRowRecord]
    error_message: str | None = None
    actual_page_number: int | None = None
    redirected: bool = False


@dataclass(frozen=True)
class FilteredPublicationRecord:
    space_id: str
    folder_id: str
    page_number: int
    row_key: str
    publication_number: str
    date_field_name: str
    date_value: str
    parsed_date: str


@dataclass
class FolderTableProbeSummary:
    folder_id: str
    space_id: str
    output_dir: Path
    successful_pages: list[int] = field(default_factory=list)
    failed_pages: list[int] = field(default_factory=list)
    total_rows_written: int = 0
    schema: TableSchema | None = None

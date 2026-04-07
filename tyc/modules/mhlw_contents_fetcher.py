from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from loguru import logger
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_OUTPUT_DIR = Path("tyc/data/output/mhlw_contents")
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_WAIT_TIMEOUT_MS = DEFAULT_TIMEOUT_SECONDS * 1000
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY_SECONDS = 1.0
DEFAULT_BROWSER_EXECUTABLE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)
MAX_FILENAME_STEM_LENGTH = 120
PREFERRED_QUERY_KEYS = ("page", "tid", "iid", "id", "article", "chapter")


def build_output_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    path_parts = [part for part in unquote(parsed.path.strip("/")).split("/") if part]
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query_map = {key: value for key, value in query_pairs if key}
    short_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]

    name_parts = [parsed.netloc.replace(".", "_")]
    if path_parts:
        name_parts.append(path_parts[-1])

    for key in PREFERRED_QUERY_KEYS:
        value = query_map.get(key)
        if value:
            name_parts.append(f"{key}_{value}")

    name_parts.append(short_hash)
    raw_name = "__".join(name_parts) if name_parts else f"mhlw_go_jp__{short_hash}"
    safe_name = re.sub(r'[<>:"/\\|?*\s]+', "_", raw_name).strip("._")
    if not safe_name:
        safe_name = f"mhlw_go_jp__{short_hash}"
    safe_name = safe_name[:MAX_FILENAME_STEM_LENGTH].rstrip("._")
    return f"{safe_name}.txt"


def normalize_text(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines()]
    cleaned_lines = [line for line in lines if line]
    text = "\n".join(cleaned_lines).strip()
    return text


def build_launch_options() -> dict[str, object]:
    launch_options: dict[str, object] = {"headless": True}
    browser_path = Path(DEFAULT_BROWSER_EXECUTABLE_PATH)
    if browser_path.exists():
        launch_options["executable_path"] = str(browser_path)
    return launch_options


def fetch_contents_text(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retry_count: int = DEFAULT_RETRY_COUNT,
) -> str:
    wait_timeout_ms = max(timeout, 1) * 1000
    last_error: Exception | None = None

    for attempt in range(1, retry_count + 1):
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**build_launch_options())
                page = browser.new_page(
                    user_agent=DEFAULT_USER_AGENT,
                    locale="ja-JP",
                )
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=wait_timeout_ms)
                    page.wait_for_selector("#contents", state="visible", timeout=wait_timeout_ms)
                    raw_text = page.locator("#contents").inner_text(timeout=wait_timeout_ms)
                    text = normalize_text(raw_text)
                    if not text:
                        raise ValueError("The contents element was found, but it did not contain text.")
                    return text
                finally:
                    browser.close()
        except (PlaywrightTimeoutError, PlaywrightError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "[mhlw_contents_fetcher] attempt "
                f"{attempt}/{retry_count} failed for {url}: {exc}"
            )
            if attempt < retry_count:
                time.sleep(DEFAULT_RETRY_DELAY_SECONDS)

    if last_error is None:
        raise RuntimeError(f"Failed to fetch contents text from {url}")
    raise last_error


def save_contents_text(
    text: str,
    source_url: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    output_filename: str | None = None,
) -> Path:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    filename = output_filename or build_output_filename_from_url(source_url)
    output_path = output_dir_path / filename
    output_path.write_text(text, encoding="utf-8")
    return output_path


def fetch_and_save_contents(
    url: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    output_filename: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Path:
    text = fetch_contents_text(url, timeout=timeout)
    return save_contents_text(
        text=text,
        source_url=url,
        output_dir=output_dir,
        output_filename=output_filename,
    )

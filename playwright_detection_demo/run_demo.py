"""Controller that starts the local server and then runs Playwright automation."""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

from playwright.sync_api import sync_playwright

if __package__ in {None, ""}:
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from playwright_detection_demo.automation_runner import run_automation
    from playwright_detection_demo.detection_server import create_server
else:
    from .automation_runner import run_automation
    from .detection_server import create_server

LOGGER = logging.getLogger("playwright_detection_demo.controller")
HOST = "127.0.0.1"
PORT = 8008
BASE_URL = f"http://{HOST}:{PORT}/"


def wait_for_server_ready(base_url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    health_url = f"{base_url.rstrip('/')}/health"
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.5) as response:
                if response.status == 200:
                    LOGGER.info("server is ready: %s", health_url)
                    return
        except Exception as error:  # noqa: BLE001
            last_error = error
            time.sleep(0.25)

    raise RuntimeError(f"server did not become ready in time: {last_error}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    server = create_server(HOST, PORT)
    server_thread = threading.Thread(target=server.serve_forever, name="detection-demo-server", daemon=True)

    try:
        LOGGER.info("starting detection demo server on %s", BASE_URL)
        server_thread.start()
        wait_for_server_ready(BASE_URL)

        with sync_playwright() as playwright:
            automation_result = run_automation(playwright, BASE_URL)

        server.store.wait_for_reports(minimum=3, timeout=3.0)
        LOGGER.info("automation result: %s", json.dumps(automation_result, ensure_ascii=False, indent=2))
        LOGGER.info(
            "collected browser reports: %s",
            json.dumps(server.store.reports, ensure_ascii=False, indent=2),
        )
        LOGGER.info(
            "captured request headers: %s",
            json.dumps(server.store.request_logs, ensure_ascii=False, indent=2),
        )
    finally:
        LOGGER.info("shutting down detection demo server")
        server.shutdown()
        server.server_close()
        with suppress(RuntimeError):
            server_thread.join(timeout=2.0)


if __name__ == "__main__":
    main()

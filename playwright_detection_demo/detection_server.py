"""Local HTTP server that records browser fingerprint signals."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

LOGGER = logging.getLogger("playwright_detection_demo.server")
DOWNLOAD_FILENAME = "demo-report.txt"
DOWNLOAD_CONTENT = (
    "This file is served by the local detection demo.\n"
    "If Playwright downloads this file, the click flow worked.\n"
).encode("utf-8")


@dataclass
class DetectionStore:
    """Thread-safe storage for browser reports collected by the server."""

    reports: list[dict[str, Any]] = field(default_factory=list)
    request_logs: list[dict[str, Any]] = field(default_factory=list)
    _condition: threading.Condition = field(default_factory=threading.Condition, init=False, repr=False)

    def add_report(self, report: dict[str, Any]) -> None:
        with self._condition:
            self.reports.append(report)
            self._condition.notify_all()

    def add_request_log(self, request_log: dict[str, Any]) -> None:
        with self._condition:
            self.request_logs.append(request_log)
            self._condition.notify_all()

    def wait_for_reports(self, minimum: int, timeout: float) -> bool:
        with self._condition:
            return self._condition.wait_for(lambda: len(self.reports) >= minimum, timeout=timeout)


def _html_response(title: str, body: str) -> bytes:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{
      font-family: "Segoe UI", sans-serif;
      margin: 40px;
      background: #f5f7fb;
      color: #1b1f24;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
      background: white;
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font-size: 16px;
      cursor: pointer;
      background: #0f62fe;
      color: white;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #f0f4ff;
      padding: 16px;
      border-radius: 12px;
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""
    return html.encode("utf-8")


HOME_PAGE = _html_response(
    "Detection Demo Home",
    """
    <h1>Local Browser Detection Demo</h1>
    <p>This page collects browser signals with JavaScript and reports them back to the local server.</p>
    <button id="go-detail-button" type="button">Open Detail Page</button>
    <pre id="page-state">Waiting for browser signal collection...</pre>
    <script>
      async function collectSignals(pageName) {
        const permissionsState = await navigator.permissions
          .query({ name: "notifications" })
          .then(result => result.state)
          .catch(error => `error: ${error.message}`);

        const canvas = document.createElement("canvas");
        canvas.width = 240;
        canvas.height = 60;
        const ctx = canvas.getContext("2d");
        ctx.textBaseline = "top";
        ctx.font = "16px Arial";
        ctx.fillStyle = "#f60";
        ctx.fillRect(10, 10, 100, 30);
        ctx.fillStyle = "#069";
        ctx.fillText("Playwright demo", 14, 16);

        const webglCanvas = document.createElement("canvas");
        const gl = webglCanvas.getContext("webgl") || webglCanvas.getContext("experimental-webgl");
        const debugInfo = gl && gl.getExtension("WEBGL_debug_renderer_info");
        const webglInfo = gl ? {
          vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
          renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
          version: gl.getParameter(gl.VERSION)
        } : null;

        return {
          page_name: pageName,
          current_url: window.location.href,
          navigator_webdriver: navigator.webdriver,
          navigator_webdriver_is_undefined: navigator.webdriver === undefined,
          navigator_webdriver_display: navigator.webdriver === undefined ? "undefined" : String(navigator.webdriver),
          has_window_chrome: Boolean(window.chrome),
          chrome_keys: window.chrome ? Object.keys(window.chrome).slice(0, 10) : [],
          plugins_count: navigator.plugins ? navigator.plugins.length : 0,
          plugins: Array.from(navigator.plugins || []).map(plugin => plugin.name),
          languages: Array.from(navigator.languages || []),
          language: navigator.language || null,
          permissions_notifications: permissionsState,
          canvas_fingerprint: canvas.toDataURL(),
          webgl_info: webglInfo,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          user_agent: navigator.userAgent,
          platform: navigator.platform,
          timestamp: new Date().toISOString()
        };
      }

      async function reportSignals(pageName) {
        const signals = await collectSignals(pageName);
        document.getElementById("page-state").textContent = JSON.stringify(signals, null, 2);
        await fetch("/api/report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(signals)
        });
      }

      window.addEventListener("load", () => {
        reportSignals("home_page");
      });

      document.getElementById("go-detail-button").addEventListener("click", () => {
        window.location.href = "/detail";
      });
    </script>
    """,
)


DETAIL_PAGE = _html_response(
    "Detection Demo Detail",
    f"""
    <h1>Detail Page</h1>
    <p>The download button reports signals first, then triggers a file download from the local server.</p>
    <button id="download-button" type="button">Download Demo File</button>
    <pre id="detail-state">Waiting for browser signal collection...</pre>
    <script>
      async function collectSignals(pageName) {{
        const permissionsState = await navigator.permissions
          .query({{ name: "notifications" }})
          .then(result => result.state)
          .catch(error => `error: ${{error.message}}`);

        const canvas = document.createElement("canvas");
        canvas.width = 240;
        canvas.height = 60;
        const ctx = canvas.getContext("2d");
        ctx.textBaseline = "top";
        ctx.font = "16px Arial";
        ctx.fillStyle = "#111";
        ctx.fillRect(12, 12, 96, 28);
        ctx.fillStyle = "#3ddc97";
        ctx.fillText("Detail page probe", 16, 18);

        const webglCanvas = document.createElement("canvas");
        const gl = webglCanvas.getContext("webgl") || webglCanvas.getContext("experimental-webgl");
        const debugInfo = gl && gl.getExtension("WEBGL_debug_renderer_info");
        const webglInfo = gl ? {{
          vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
          renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
          version: gl.getParameter(gl.VERSION)
        }} : null;

        return {{
          page_name: pageName,
          current_url: window.location.href,
          navigator_webdriver: navigator.webdriver,
          navigator_webdriver_is_undefined: navigator.webdriver === undefined,
          navigator_webdriver_display: navigator.webdriver === undefined ? "undefined" : String(navigator.webdriver),
          has_window_chrome: Boolean(window.chrome),
          chrome_keys: window.chrome ? Object.keys(window.chrome).slice(0, 10) : [],
          plugins_count: navigator.plugins ? navigator.plugins.length : 0,
          plugins: Array.from(navigator.plugins || []).map(plugin => plugin.name),
          languages: Array.from(navigator.languages || []),
          language: navigator.language || null,
          permissions_notifications: permissionsState,
          canvas_fingerprint: canvas.toDataURL(),
          webgl_info: webglInfo,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          user_agent: navigator.userAgent,
          platform: navigator.platform,
          timestamp: new Date().toISOString()
        }};
      }}

      async function reportSignals(pageName) {{
        const signals = await collectSignals(pageName);
        document.getElementById("detail-state").textContent = JSON.stringify(signals, null, 2);
        await fetch("/api/report", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(signals)
        }});
      }}

      window.addEventListener("load", () => {{
        reportSignals("detail_page");
      }});

      document.getElementById("download-button").addEventListener("click", async () => {{
        await reportSignals("detail_download_click");
        window.location.href = "/download/{DOWNLOAD_FILENAME}";
      }});
    </script>
    """,
)


class DetectionRequestHandler(BaseHTTPRequestHandler):
    """HTTP endpoints for the local browser detection demo."""

    server: "DetectionHTTPServer"

    def _json_response(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record_request(self) -> None:
        parsed = urlparse(self.path)
        request_log = {
            "path": parsed.path,
            "method": self.command,
            "user_agent": self.headers.get("User-Agent", ""),
            "accept_language": self.headers.get("Accept-Language", ""),
            "sec_ch_ua": self.headers.get("Sec-CH-UA", ""),
            "referer": self.headers.get("Referer", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.server.store.add_request_log(request_log)
        LOGGER.info("request %s %s", self.command, json.dumps(request_log, ensure_ascii=False))

    def do_GET(self) -> None:  # noqa: N802
        self._record_request()

        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json_response(HTTPStatus.OK, {"status": "ok"})
            return
        if parsed.path == "/":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HOME_PAGE)))
            self.end_headers()
            self.wfile.write(HOME_PAGE)
            return
        if parsed.path == "/detail":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(DETAIL_PAGE)))
            self.end_headers()
            self.wfile.write(DETAIL_PAGE)
            return
        if parsed.path == f"/download/{DOWNLOAD_FILENAME}":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{DOWNLOAD_FILENAME}"')
            self.send_header("Content-Length", str(len(DOWNLOAD_CONTENT)))
            self.end_headers()
            self.wfile.write(DOWNLOAD_CONTENT)
            return
        if parsed.path == "/api/reports":
            self._json_response(
                HTTPStatus.OK,
                {
                    "reports": self.server.store.reports,
                    "request_logs": self.server.store.request_logs,
                },
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        self._record_request()

        parsed = urlparse(self.path)
        if parsed.path != "/api/report":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        payload = json.loads(raw_body.decode("utf-8"))
        payload["server_received_at"] = datetime.now(timezone.utc).isoformat()
        self.server.store.add_report(payload)
        LOGGER.info("browser_report %s", json.dumps(payload, ensure_ascii=False))
        self._json_response(HTTPStatus.OK, {"received": True, "report_count": len(self.server.store.reports)})

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.debug("%s - %s", self.address_string(), format % args)


class DetectionHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server with shared detection storage."""

    def __init__(self, server_address: tuple[str, int], store: DetectionStore):
        super().__init__(server_address, DetectionRequestHandler)
        self.store = store


def create_server(host: str = "127.0.0.1", port: int = 8008) -> DetectionHTTPServer:
    return DetectionHTTPServer((host, port), DetectionStore())

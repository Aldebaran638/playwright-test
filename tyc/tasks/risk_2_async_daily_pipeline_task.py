#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2_async.main import (
    Risk2AsyncConfig,
    load_companies_from_file,
    process_risk_2_async,
    save_risk_results,
)
from tyc.modules.risk_daily.risk_daily_converter import convert_risk_results_file
from tyc.modules.risk_daily.risk_daily_db_uploader import (
    RiskDailyDbConfig,
    mask_db_config,
    test_db_connection,
    upload_risk_daily_summary_to_db,
)


DEFAULT_COMPANIES_FILE = "tyc/data/input/name_list_test.txt"
DEFAULT_RISK_OUTPUT_FILE = "tyc/data/output/risk_2_async_results.json"
DEFAULT_DAILY_OUTPUT_FILE = "tyc/data/output/risk_2_async_daily_summary.json"
DEFAULT_SEARCH_URL = "https://www.tianyancha.com/risk"
DEFAULT_HOME_URL = "https://www.tianyancha.com/"
DEFAULT_RISK_DATE_START = "2025-10-01"
DEFAULT_RISK_DATE_END = "2026-12-31"
DEFAULT_CONVERT_DATE_START = DEFAULT_RISK_DATE_START
DEFAULT_CONVERT_DATE_END = DEFAULT_RISK_DATE_END
DEFAULT_MAX_QUERY_COUNT = 100
DEFAULT_MAX_PAGE_TURNS = 20
DEFAULT_WORKER_COUNT = 4
DEFAULT_BROWSER_EXECUTABLE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEFAULT_USER_DATA_DIR = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
DEFAULT_HEADLESS = False
DEFAULT_PAUSE_EVERY_N_COMPANIES = 10
DEFAULT_PAUSE_SECONDS = 5.0
DEFAULT_DB_HOST = "192.168.2.212"
DEFAULT_DB_PORT = 3306
DEFAULT_DB_USER = "root"
DEFAULT_DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DEFAULT_DB_NAME = "winkeyai"
DEFAULT_DB_TABLE = "risk_info_test"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行异步 risk_2 查询、日汇总转换、数据库上传三步流水线")
    parser.add_argument("--companies-file", default=DEFAULT_COMPANIES_FILE)
    parser.add_argument("--risk-output-file", default=DEFAULT_RISK_OUTPUT_FILE)
    parser.add_argument("--daily-output-file", default=DEFAULT_DAILY_OUTPUT_FILE)
    parser.add_argument("--search-url", default=DEFAULT_SEARCH_URL)
    parser.add_argument("--home-url", default=DEFAULT_HOME_URL)
    parser.add_argument("--risk-date-start", default=DEFAULT_RISK_DATE_START)
    parser.add_argument("--risk-date-end", default=DEFAULT_RISK_DATE_END)
    parser.add_argument("--convert-date-start", default=DEFAULT_CONVERT_DATE_START)
    parser.add_argument("--convert-date-end", default=DEFAULT_CONVERT_DATE_END)
    parser.add_argument("--max-query-count", type=int, default=DEFAULT_MAX_QUERY_COUNT)
    parser.add_argument("--max-page-turns", type=int, default=DEFAULT_MAX_PAGE_TURNS)
    parser.add_argument("--worker-count", type=int, default=DEFAULT_WORKER_COUNT)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--pause-every-n-companies", type=int, default=DEFAULT_PAUSE_EVERY_N_COMPANIES)
    parser.add_argument("--pause-seconds", type=float, default=DEFAULT_PAUSE_SECONDS)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    parser.add_argument("--db-host", default=DEFAULT_DB_HOST)
    parser.add_argument("--db-port", type=int, default=DEFAULT_DB_PORT)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=DEFAULT_DB_PASSWORD)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--db-table", default=DEFAULT_DB_TABLE)
    parser.add_argument("--skip-connection-test", action="store_true", default=False)
    return parser


def build_form_fields(parser: argparse.ArgumentParser) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for action in parser._actions:
        if not action.option_strings or action.dest == "help":
            continue

        field_kind = "checkbox" if isinstance(action, argparse._StoreTrueAction) else "input"
        input_type = "text"
        if field_kind != "checkbox":
            if action.type is int:
                input_type = "int"
            elif action.type is float:
                input_type = "float"
            elif "password" in action.dest:
                input_type = "password"

        fields.append(
            {
                "name": action.dest,
                "label": action.dest.replace("_", " "),
                "kind": field_kind,
                "input_type": input_type,
                "default": action.default if action.default is not argparse.SUPPRESS else "",
                "option": action.option_strings[0],
            }
        )
    return fields


def build_args_from_values(parser: argparse.ArgumentParser, values: dict[str, Any]) -> argparse.Namespace:
    cli_args: list[str] = []
    for action in parser._actions:
        if not action.option_strings or action.dest == "help":
            continue

        option_name = action.option_strings[0]
        if isinstance(action, argparse._StoreTrueAction):
            if values.get(action.dest):
                cli_args.append(option_name)
            continue

        value = values.get(action.dest, "")
        if value in ("", None):
            continue
        cli_args.extend([option_name, str(value)])

    return parser.parse_args(cli_args)


async def run_pipeline(args: argparse.Namespace) -> int:
    companies = load_companies_from_file(args.companies_file)
    if not companies:
        logger.error("[risk_2_async_daily_pipeline_task] 未读取到公司列表，流水线终止")
        return 1

    risk_config = Risk2AsyncConfig(
        search_url=args.search_url,
        home_url=args.home_url,
        date_start=args.risk_date_start,
        date_end=args.risk_date_end,
        max_query_count=args.max_query_count,
        max_page_turns=args.max_page_turns,
        worker_count=args.worker_count,
        browser_executable_path=Path(args.browser_executable_path) if args.browser_executable_path else None,
        user_data_dir=Path(args.user_data_dir) if args.user_data_dir else None,
        headless=args.headless,
        pause_every_n_companies=args.pause_every_n_companies,
        pause_seconds=args.pause_seconds,
    )
    db_config = RiskDailyDbConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        table=args.db_table,
    )

    logger.info("[risk_2_async_daily_pipeline_task] 第一步：执行异步 risk_2 抓取")
    results, failed_companies = await process_risk_2_async(companies, config=risk_config)
    save_risk_results(
        args.risk_output_file,
        results,
        failed_companies,
        date_start=risk_config.date_start,
        date_end=risk_config.date_end,
        worker_count=risk_config.worker_count,
    )

    logger.info("[risk_2_async_daily_pipeline_task] 第二步：执行按日汇总转换")
    converted_records = convert_risk_results_file(
        args.risk_output_file,
        args.daily_output_file,
        start_date=args.convert_date_start,
        end_date=args.convert_date_end,
    )
    logger.info(f"[risk_2_async_daily_pipeline_task] 转换完成，记录数: {len(converted_records)}")

    logger.info(f"[risk_2_async_daily_pipeline_task] 第三步：执行数据库上传，配置: {mask_db_config(db_config)}")
    if not args.skip_connection_test and not test_db_connection(db_config):
        logger.error("[risk_2_async_daily_pipeline_task] 数据库连接测试失败，流水线终止")
        return 1

    if not upload_risk_daily_summary_to_db(args.daily_output_file, db_config):
        logger.error("[risk_2_async_daily_pipeline_task] 数据库上传失败")
        return 1

    logger.info(
        f"[risk_2_async_daily_pipeline_task] 流水线完成，成功公司数: {len(results)}，失败公司数: {len(failed_companies)}"
    )
    return 0


class QueueLogSink:
    def __init__(self, callback: Any) -> None:
        self.callback = callback

    def __call__(self, message: str) -> None:
        self.callback(message.rstrip("\n"))


class PipelineGui:
    def __init__(self, parser: argparse.ArgumentParser) -> None:
        self.parser = parser
        self.fields = build_form_fields(parser)
        self.root = tk.Tk()
        self.root.title("risk_2_async daily pipeline")
        self.root.geometry("1080x780")
        self.root.minsize(960, 680)

        self.status_var = tk.StringVar(value="填写参数后点击“运行流水线”")
        self.widgets: dict[str, tk.Variable | ttk.Entry] = {}
        self.running = False

        self._build_layout()

    def _build_layout(self) -> None:
        style = ttk.Style()
        style.configure("Header.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Hint.TLabel", foreground="#5b6472")

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)
        container.rowconfigure(2, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="risk_2_async daily pipeline", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="桌面表单会自动读取命令行参数和默认值，不再启动本地网页服务。",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        form_outer = ttk.Frame(container)
        form_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        form_outer.columnconfigure(0, weight=1)
        form_outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(form_outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_outer, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, padding=8)

        scroll_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        form_outer.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width - scrollbar.winfo_width()),
        )

        for col in range(4):
            scroll_frame.columnconfigure(col, weight=1)

        row = 0
        col = 0
        for field in self.fields:
            if field["kind"] == "checkbox":
                var = tk.BooleanVar(value=bool(field["default"]))
                widget = ttk.Checkbutton(
                    scroll_frame,
                    text=f'{field["label"]} ({field["option"]})',
                    variable=var,
                )
                widget.grid(row=row, column=0, columnspan=4, sticky="w", padx=8, pady=8)
                self.widgets[field["name"]] = var
                row += 1
                col = 0
                continue

            frame = ttk.Frame(scroll_frame, padding=8)
            frame.grid(row=row, column=col, sticky="nsew")
            frame.columnconfigure(0, weight=1)

            ttk.Label(frame, text=field["label"]).grid(row=0, column=0, sticky="w")
            ttk.Label(frame, text=field["option"], style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 4))

            show = "*" if field["input_type"] == "password" else ""
            entry = ttk.Entry(frame, show=show)
            entry.grid(row=2, column=0, sticky="ew")
            entry.insert(0, "" if field["default"] is None else str(field["default"]))

            self.widgets[field["name"]] = entry
            col += 1
            if col >= 2:
                col = 0
                row += 1

        if col != 0:
            row += 1

        action_bar = ttk.Frame(container)
        action_bar.grid(row=2, column=0, sticky="nsew")
        action_bar.columnconfigure(0, weight=1)
        action_bar.rowconfigure(1, weight=1)

        status_frame = ttk.Frame(action_bar)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        self.run_button = ttk.Button(status_frame, text="运行流水线", command=self.start_run)
        self.run_button.pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(action_bar, wrap=tk.WORD, height=18)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self.log_text.configure(state=tk.DISABLED)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_running(self, running: bool) -> None:
        self.running = running
        self.run_button.configure(state=tk.DISABLED if running else tk.NORMAL)

    def collect_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field in self.fields:
            widget = self.widgets[field["name"]]
            if field["kind"] == "checkbox":
                values[field["name"]] = bool(widget.get())  # type: ignore[union-attr]
            else:
                values[field["name"]] = widget.get().strip()  # type: ignore[union-attr]
        return values

    def start_run(self) -> None:
        if self.running:
            return

        values = self.collect_values()
        try:
            args = build_args_from_values(self.parser, values)
        except SystemExit:
            messagebox.showerror("参数错误", "输入参数无法解析，请检查数字和必填项格式。")
            return

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.status_var.set("运行中...")
        self._set_running(True)

        thread = threading.Thread(target=self._run_pipeline_thread, args=(args,), daemon=True)
        thread.start()

    def _run_pipeline_thread(self, args: argparse.Namespace) -> None:
        sink_id = logger.add(QueueLogSink(lambda msg: self.root.after(0, self._append_log, msg)))
        try:
            exit_code = asyncio.run(run_pipeline(args))
            self.root.after(0, self._finish_run, exit_code)
        except Exception as exc:
            logger.exception("[risk_2_async_daily_pipeline_task] GUI execution crashed")
            self.root.after(0, self._append_log, f"{type(exc).__name__}: {exc}")
            self.root.after(0, self._finish_run, 1)
        finally:
            logger.remove(sink_id)

    def _finish_run(self, exit_code: int) -> None:
        self._set_running(False)
        if exit_code == 0:
            self.status_var.set("运行完成")
        else:
            self.status_var.set(f"运行失败，退出码: {exit_code}")

    def run(self) -> None:
        self.root.mainloop()


def run_gui() -> None:
    gui = PipelineGui(build_parser())
    gui.run()


def main() -> None:
    if "--gui" in sys.argv[1:]:
        run_gui()
        return

    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run_pipeline(args)))


if __name__ == "__main__":
    main()

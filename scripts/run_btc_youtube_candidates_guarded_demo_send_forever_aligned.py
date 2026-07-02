#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILD = REPO_ROOT / "scripts" / "run_btc_youtube_candidates_guarded_demo_send_once.py"
DEFAULT_LOG_BASE = Path("data/runtime_logs/btc")
DEFAULT_STATE_DIR = Path("data/runtime_state/btc/youtube_candidates")
COLUMNS = [
    "cycle_index", "cycle_start_utc", "cycle_end_utc", "returncode", "cycle_ok",
    "classification", "trade_notifications", "monitor_notifications", "order_payloads",
    "order_gate_passed", "sender_sent_rows", "next_run_utc", "stdout_log", "stderr_log", "summary_json",
]


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def mkdirp(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    mkdirp(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"cycle_ok": False, "classification": f"SUMMARY_READ_ERROR: {exc}"}


def append_csv(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in COLUMNS})


def week_dir(base: Path) -> Path:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return base / f"{year:04d}" / f"{now.month:02d}" / f"week_{week:02d}" / "youtube_candidates"


def next_aligned(now: datetime, interval_minutes: int, offset_seconds: int) -> datetime:
    base = now.replace(second=0, microsecond=0)
    minute = ((base.minute // interval_minutes) + 1) * interval_minutes
    if minute >= 60:
        base = base.replace(minute=0) + timedelta(hours=1)
    else:
        base = base.replace(minute=minute)
    return base + timedelta(seconds=offset_seconds)


def build_cmd(args: argparse.Namespace, out_dir: Path) -> list[str]:
    cmd = [
        sys.executable, str(CHILD),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(out_dir),
        "--state-dir", str(args.state_dir),
        "--broker-symbol", args.broker_symbol,
        "--expected-login", str(args.expected_login),
        "--deviation", str(args.deviation),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--discord-webhook-env", args.discord_webhook_env,
        "--discord-username", args.discord_username,
    ]
    for value, flag in [(args.m5_csv, "--m5-csv"), (args.m15_csv, "--m15-csv"), (args.h4_csv, "--h4-csv")]:
        if value:
            cmd.extend([flag, value])
    if args.discord_webhook_url:
        cmd.extend(["--discord-webhook-url", args.discord_webhook_url])
    if args.send:
        cmd.append("--send")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    return cmd


def run_fast_manager(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    report_path = root / "latest_fast_position_manager_report.json"
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "manage_btc_youtube_positions.py"),
        "--state-json", str(args.state_dir / "btc4_split_position_state.json"),
        "--report-json", str(report_path),
        "--symbol", args.broker_symbol,
        "--expected-login", str(args.expected_login),
        "--require-demo-account",
        "--require-hedging",
    ]
    if args.send and args.allow_demo_send:
        cmd.append("--send")
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    report = read_json(report_path)
    if proc.returncode != 0 or not report.get("cycle_ok", False):
        error_log = root / "fast_manager_errors.log"
        mkdirp(error_log.parent)
        with error_log.open("a", encoding="utf-8") as handle:
            handle.write(f"[{utc_text()}] rc={proc.returncode} report={json.dumps(report, ensure_ascii=False, default=str)}\n")
            if proc.stderr:
                handle.write(proc.stderr + "\n")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persistent aligned YouTube BTC candidate Discord/demo-autotrade loop.")
    parser.add_argument("--log-base", type=Path, default=DEFAULT_LOG_BASE)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--m5-csv", default="")
    parser.add_argument("--m15-csv", default="")
    parser.add_argument("--h4-csv", default="")
    parser.add_argument("--interval-minutes", type=int, default=1)
    parser.add_argument("--offset-seconds", type=int, default=10)
    parser.add_argument("--broker-symbol", default="BTCUSD#")
    parser.add_argument("--expected-login", type=int, default=75539039)
    parser.add_argument("--deviation", type=int, default=100)
    parser.add_argument("--max-symbol-positions", type=int, default=6)
    parser.add_argument("--max-symbol-lot", type=float, default=0.10)
    parser.add_argument("--discord-webhook-url", default="")
    parser.add_argument("--discord-webhook-env", default="DISCORD_WEBHOOK_URL")
    parser.add_argument("--discord-username", default="Mochipoyo BTC YouTube")
    parser.add_argument("--manager-interval-seconds", type=float, default=2.0)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--allow-demo-send", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.log_base = args.log_base if args.log_base.is_absolute() else REPO_ROOT / args.log_base
    args.state_dir = args.state_dir if args.state_dir.is_absolute() else REPO_ROOT / args.state_dir
    mkdirp(args.log_base)
    mkdirp(args.state_dir)
    cycle_index = 0
    try:
        while True:
            cycle_index += 1
            root = week_dir(args.log_base)
            run_dir = root / "child_runs" / f"cycle_{cycle_index:06d}_{stamp()}"
            stdout_path = root / "cycle_logs" / f"cycle_{cycle_index:06d}_{stamp()}_stdout.log"
            stderr_path = root / "cycle_logs" / f"cycle_{cycle_index:06d}_{stamp()}_stderr.log"
            mkdirp(run_dir)
            start = utc_now()
            process = subprocess.run(
                build_cmd(args, run_dir), cwd=str(REPO_ROOT), capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
            mkdirp(stdout_path.parent)
            stdout_path.write_text(process.stdout or "", encoding="utf-8")
            stderr_path.write_text(process.stderr or "", encoding="utf-8")
            summary_path = run_dir / "latest_btc_youtube_candidates_guarded_demo_send_once_result.json"
            summary = read_json(summary_path)
            next_run = next_aligned(utc_now(), args.interval_minutes, args.offset_seconds)
            row = {
                "cycle_index": cycle_index,
                "cycle_start_utc": utc_text(start),
                "cycle_end_utc": utc_text(),
                "returncode": process.returncode,
                "cycle_ok": bool(process.returncode == 0 and summary.get("cycle_ok")),
                "classification": summary.get("classification", "NO_SUMMARY"),
                "trade_notifications": summary.get("rows", {}).get("trade_notifications", 0),
                "monitor_notifications": summary.get("rows", {}).get("monitor_notifications", 0),
                "order_payloads": summary.get("rows", {}).get("order_payloads", 0),
                "order_gate_passed": summary.get("guards", {}).get("order_gate_passed", False),
                "sender_sent_rows": summary.get("sender_report", {}).get("sent_rows", 0),
                "next_run_utc": utc_text(next_run),
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "summary_json": str(summary_path),
            }
            append_csv(root / "aligned_loop_log.csv", row)
            write_json(root / "latest_loop_state.json", {
                "schema_version": "btc_youtube_aligned_loop_v1",
                "updated_at_utc": utc_text(),
                "last_cycle": row,
                "persistent_state_dir": str(args.state_dir),
            })
            print(
                f"[CYCLE {cycle_index}] ok={row['cycle_ok']} class={row['classification']} "
                f"notify={row['trade_notifications']}+{row['monitor_notifications']} "
                f"orders={row['order_payloads']} sent={row['sender_sent_rows']}",
                flush=True,
            )
            if args.max_cycles > 0 and cycle_index >= args.max_cycles:
                return 0 if row["cycle_ok"] else 1
            while utc_now() < next_run:
                run_fast_manager(args, root)
                remaining = (next_run - utc_now()).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(max(0.2, min(float(args.manager_interval_seconds), remaining)))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
ONCE_SCRIPT = REPO_ROOT / "scripts" / "run_btc_youtube_candidates_guarded_demo_send_once.py"
SHADOW_SCRIPT = REPO_ROOT / "scripts" / "manage_btc6_shadow_trades.py"
POSITION_MANAGER_SCRIPT = REPO_ROOT / "scripts" / "manage_btc_youtube_positions.py"
DISCORD_SCRIPT = REPO_ROOT / "scripts" / "send_mochipoyo_discord_messages.py"
DEFAULT_FILES_DIR = REPO_ROOT / "Files"
DEFAULT_LOG_BASE = REPO_ROOT / "data" / "runtime_logs" / "btc"
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "runtime_state" / "btc" / "youtube_candidates"
LOOP_COLUMNS = [
    "cycle_index", "cycle_start_utc", "cycle_end_utc", "cycle_ok", "classification",
    "once_returncode", "btc6_shadow_ok", "btc6_new_events", "btc6_open_trades",
    "btc6_closed_trades", "btc6_total_r", "btc6_total_pips", "btc6_discord_status",
    "m5_csv", "m15_csv", "h4_csv", "error", "next_run_utc",
    "once_summary_json", "shadow_summary_json", "stdout_log", "stderr_log",
]


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def mkdirp(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, value: Any) -> None:
    mkdirp(path.parent)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    path.write_text(text, encoding="utf-8")


def append_csv(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOOP_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in LOOP_COLUMNS})


def week_dir(base: Path) -> Path:
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return base / f"{year:04d}" / f"{now.month:02d}" / f"week_{week:02d}" / "youtube_candidates_operational"


def stable_log_dir(base: Path) -> Path:
    return base / "youtube_candidates_operational"


def next_aligned(now: datetime, interval_minutes: int, offset_seconds: int) -> datetime:
    base = now.replace(second=0, microsecond=0)
    minute = ((base.minute // interval_minutes) + 1) * interval_minutes
    if minute >= 60:
        base = base.replace(minute=0) + timedelta(hours=1)
    else:
        base = base.replace(minute=minute)
    return base + timedelta(seconds=offset_seconds)


def _available_live_csvs(files_dir: Path) -> list[Path]:
    if not files_dir.exists():
        return []
    return sorted(
        path for path in files_dir.iterdir()
        if path.is_file()
        and path.name.lower().startswith("btcusdsharp_")
        and path.suffix.lower() == ".csv"
    )


def _normalized_suffix(path: Path) -> tuple[str, set[str]]:
    stem = path.stem.lower()
    prefix = "btcusdsharp_"
    suffix = stem[len(prefix):] if stem.startswith(prefix) else stem
    normalized = re.sub(r"[^a-z0-9]", "", suffix)
    tokens = {token for token in re.split(r"[^a-z0-9]+", suffix) if token}
    tokens.add(normalized)
    return normalized, tokens


def resolve_live_csv(files_dir: Path, timeframe: str) -> Path:
    aliases = {
        "m5": {"m5", "5m", "5", "05", "m05", "5min", "min5"},
        "m15": {"m15", "15m", "15", "015", "m015", "15min", "min15"},
        "h4": {"h4", "4h", "4", "04", "240", "240m", "4hour", "4hours"},
    }[timeframe]
    candidates = _available_live_csvs(files_dir)
    exact_name = f"btcusdsharp_{timeframe}.csv"
    exact = [path for path in candidates if path.name.lower() == exact_name]
    if len(exact) == 1:
        return exact[0]

    matched: list[Path] = []
    for path in candidates:
        normalized, tokens = _normalized_suffix(path)
        if normalized in aliases or aliases.intersection(tokens):
            matched.append(path)
    if len(matched) == 1:
        return matched[0]
    available = [path.name for path in candidates]
    if not matched:
        raise FileNotFoundError(
            f"{timeframe} live CSV was not found under {files_dir}. "
            f"Expected btcusdsharp_*.csv. Available={available}"
        )
    raise RuntimeError(
        f"Multiple {timeframe} CSV files matched under {files_dir}: {[path.name for path in matched]}"
    )


def validate_runtime_files(files_dir: Path) -> dict[str, Path]:
    if not files_dir.exists():
        raise FileNotFoundError(f"Live candle directory does not exist: {files_dir}")
    for script in [ONCE_SCRIPT, SHADOW_SCRIPT, POSITION_MANAGER_SCRIPT, DISCORD_SCRIPT]:
        if not script.exists():
            raise FileNotFoundError(f"Required runtime script is missing: {script}")
    resolved = {
        "m5": resolve_live_csv(files_dir, "m5"),
        "m15": resolve_live_csv(files_dir, "m15"),
        "h4": resolve_live_csv(files_dir, "h4"),
    }
    empty = [str(path) for path in resolved.values() if path.stat().st_size <= 0]
    if empty:
        raise ValueError(f"Live candle CSV is empty: {empty}")
    return resolved


def run_capture(
    cmd: list[str], *, stdout_path: Path, stderr_path: Path,
    latest_stdout_path: Path | None = None, latest_stderr_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    mkdirp(stdout_path.parent)
    completed = subprocess.run(
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    write_text(stdout_path, stdout_text)
    write_text(stderr_path, stderr_text)
    if latest_stdout_path is not None:
        write_text(latest_stdout_path, stdout_text)
    if latest_stderr_path is not None:
        write_text(latest_stderr_path, stderr_text)
    return completed


def once_command(args: argparse.Namespace, out_dir: Path, resolved: dict[str, Path]) -> list[str]:
    cmd = [
        sys.executable, str(ONCE_SCRIPT),
        "--csv-dir", str(args.files_dir),
        "--m5-csv", str(resolved["m5"]),
        "--m15-csv", str(resolved["m15"]),
        "--h4-csv", str(resolved["h4"]),
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
    if args.discord_webhook_url:
        cmd.extend(["--discord-webhook-url", args.discord_webhook_url])
    if args.send:
        cmd.append("--send")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    return cmd


def shadow_command(args: argparse.Namespace, once_dir: Path, shadow_out: Path, m5_csv: Path) -> list[str]:
    return [
        sys.executable, str(SHADOW_SCRIPT),
        "--candidates-csv", str(once_dir / "dry_run" / "candidates" / "btc_youtube_monitor_notification_candidates.csv"),
        "--m5-csv", str(m5_csv),
        "--state-json", str(args.state_dir / "btc6_shadow_state.json"),
        "--events-ledger-csv", str(args.state_dir / "btc6_shadow_events.csv"),
        "--trades-ledger-csv", str(args.state_dir / "btc6_shadow_trade_ledger.csv"),
        "--out-dir", str(shadow_out),
        "--lot", "0.01",
        "--spread-usd", str(args.spread_cost_usd),
        "--broker-symbol", args.broker_symbol,
    ]


def discord_command(args: argparse.Namespace, input_csv: Path, preview_txt: Path, preview_json: Path) -> list[str]:
    cmd = [
        sys.executable, str(DISCORD_SCRIPT),
        "--input-csv", str(input_csv),
        "--send-ledger-csv", str(args.state_dir / "btc6_shadow_discord_send_ledger.csv"),
        "--preview-txt", str(preview_txt),
        "--preview-json", str(preview_json),
        "--symbol", "BTC",
        "--max-rows", "10",
        "--style", "detailed",
        "--webhook-env", args.discord_webhook_env,
        "--username", args.discord_username,
    ]
    if args.discord_webhook_url:
        cmd.extend(["--webhook-url", args.discord_webhook_url])
    if args.send:
        cmd.append("--send")
    return cmd


def summarize_discord(preview_json: Path, rows: int, send_requested: bool, returncode: int | str) -> dict[str, Any]:
    if rows == 0:
        return {"status": "NO_ROWS", "rows": 0, "returncode": "SKIPPED", "cycle_ok": True}
    preview = read_json(preview_json)
    records = preview.get("records", []) if isinstance(preview.get("records"), list) else []
    sent = sum(1 for record in records if isinstance(record, dict) and bool(record.get("sent")))
    errors = sum(1 for record in records if isinstance(record, dict) and str(record.get("send_status", "")).startswith("ERROR"))
    duplicates = sum(1 for record in records if isinstance(record, dict) and bool(record.get("duplicate_existing")))
    dry = sum(1 for record in records if isinstance(record, dict) and str(record.get("send_status", "")) == "DRY_RUN_WOULD_SEND")
    if send_requested and sent == rows and errors == 0:
        status = "SENT"
    elif send_requested and duplicates == rows and errors == 0:
        status = "DUPLICATE_SKIPPED"
    elif not send_requested and dry + duplicates == rows and errors == 0:
        status = "DRY_RUN_OK"
    else:
        status = "ERROR"
    return {
        "status": status,
        "rows": rows,
        "sent_rows": sent,
        "duplicate_rows": duplicates,
        "error_rows": errors,
        "returncode": returncode,
        "cycle_ok": status in {"SENT", "DUPLICATE_SKIPPED", "DRY_RUN_OK"},
    }


def _has_active_btc4_pair(state_json: Path) -> bool:
    state = read_json(state_json)
    pairs = state.get("pairs", []) if isinstance(state.get("pairs"), list) else []
    active_statuses = {"ARMED", "PARTIAL_SEND_ANOMALY", "BE_MOVED"}
    return any(isinstance(pair, dict) and str(pair.get("status", "")) in active_statuses for pair in pairs)


def run_fast_btc4_manager(args: argparse.Namespace, root: Path, stable_root: Path) -> None:
    state_json = args.state_dir / "btc4_split_position_state.json"
    if not _has_active_btc4_pair(state_json):
        return
    report_path = stable_root / "latest_fast_btc4_position_manager_report.json"
    cmd = [
        sys.executable, str(POSITION_MANAGER_SCRIPT),
        "--state-json", str(state_json),
        "--report-json", str(report_path),
        "--symbol", args.broker_symbol,
        "--expected-login", str(args.expected_login),
        "--require-demo-account", "--require-hedging",
    ]
    if args.send and args.allow_demo_send:
        cmd.append("--send")
    completed = subprocess.run(
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if completed.returncode != 0:
        message = f"[{utc_text()}] rc={completed.returncode}\n{completed.stdout}\n{completed.stderr}\n"
        with (root / "fast_btc4_manager_errors.log").open("a", encoding="utf-8") as handle:
            handle.write(message)
        write_text(stable_root / "latest_fast_btc4_manager_error.log", message)


def _event_row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size <= 0:
        return 0
    try:
        return int(len(pd.read_csv(path, encoding="utf-8-sig")))
    except Exception:
        return 0


def _child_failure_text(label: str, completed: subprocess.CompletedProcess[str]) -> str:
    return (
        f"{label} failed with return code {completed.returncode}.\n"
        f"STDOUT:\n{completed.stdout or ''}\n"
        f"STDERR:\n{completed.stderr or ''}\n"
    )


def execute_cycle(
    args: argparse.Namespace, resolved: dict[str, Path], cycle_index: int,
    root: Path, stable_root: Path,
) -> tuple[dict[str, Any], bool]:
    cycle_start = utc_now()
    cycle_dir = root / "cycles" / f"cycle_{cycle_index:06d}_{stamp()}"
    once_dir = cycle_dir / "once"
    shadow_dir = cycle_dir / "btc6_shadow"
    mkdirp(cycle_dir)

    once_stdout = cycle_dir / "once_stdout.log"
    once_stderr = cycle_dir / "once_stderr.log"
    once_proc = run_capture(
        once_command(args, once_dir, resolved),
        stdout_path=once_stdout,
        stderr_path=once_stderr,
        latest_stdout_path=stable_root / "latest_once_stdout.log",
        latest_stderr_path=stable_root / "latest_once_stderr.log",
    )
    once_summary_path = once_dir / "latest_btc_youtube_candidates_guarded_demo_send_once_result.json"
    once_summary = read_json(once_summary_path)
    once_ok = bool(once_proc.returncode == 0 and once_summary.get("cycle_ok"))

    shadow_proc = run_capture(
        shadow_command(args, once_dir, shadow_dir, resolved["m5"]),
        stdout_path=cycle_dir / "shadow_stdout.log",
        stderr_path=cycle_dir / "shadow_stderr.log",
        latest_stdout_path=stable_root / "latest_shadow_stdout.log",
        latest_stderr_path=stable_root / "latest_shadow_stderr.log",
    )
    shadow_summary_path = shadow_dir / "latest_btc6_shadow_manager_result.json"
    shadow_summary = read_json(shadow_summary_path)
    shadow_ok = bool(shadow_proc.returncode == 0 and shadow_summary.get("cycle_ok"))

    events_csv = shadow_dir / "btc6_shadow_discord_events.csv"
    event_rows = _event_row_count(events_csv)
    discord_status: dict[str, Any] = {"status": "NO_ROWS", "cycle_ok": True, "rows": 0}
    if event_rows > 0:
        preview_txt = shadow_dir / "btc6_shadow_discord_preview.txt"
        preview_json = shadow_dir / "btc6_shadow_discord_preview.json"
        discord_proc = run_capture(
            discord_command(args, events_csv, preview_txt, preview_json),
            stdout_path=cycle_dir / "shadow_discord_stdout.log",
            stderr_path=cycle_dir / "shadow_discord_stderr.log",
            latest_stdout_path=stable_root / "latest_shadow_discord_stdout.log",
            latest_stderr_path=stable_root / "latest_shadow_discord_stderr.log",
        )
        discord_status = summarize_discord(preview_json, event_rows, args.send, discord_proc.returncode)

    errors: list[str] = []
    if not once_ok:
        errors.append(_child_failure_text("BTC4/BTC5/BTC6 detection cycle", once_proc))
    if not shadow_ok:
        errors.append(_child_failure_text("BTC6 shadow manager", shadow_proc))
    if not discord_status.get("cycle_ok"):
        errors.append(f"BTC6 lifecycle Discord notification failed: {discord_status}")
    error_text = "\n".join(errors)
    if error_text:
        write_text(stable_root / "latest_cycle_error.log", error_text)
        write_json(stable_root / "latest_cycle_error.json", {
            "cycle_at_utc": utc_text(),
            "cycle_index": cycle_index,
            "error": error_text,
            "once_summary": once_summary,
            "shadow_summary": shadow_summary,
            "discord_status": discord_status,
        })
        print(f"[ERROR] Cycle {cycle_index} failed. Details: {stable_root / 'latest_cycle_error.log'}", flush=True)
        if once_proc.stderr:
            print(once_proc.stderr[-2000:], flush=True)
        if shadow_proc.stderr:
            print(shadow_proc.stderr[-2000:], flush=True)

    metrics = shadow_summary.get("metrics", {}) if isinstance(shadow_summary.get("metrics"), dict) else {}
    cycle_ok = bool(once_ok and shadow_ok and discord_status.get("cycle_ok"))
    classification = "OPERATIONAL_PASS" if cycle_ok else "OPERATIONAL_FAILED"
    next_run = next_aligned(utc_now(), args.interval_minutes, args.offset_seconds)
    row = {
        "cycle_index": cycle_index,
        "cycle_start_utc": utc_text(cycle_start),
        "cycle_end_utc": utc_text(),
        "cycle_ok": cycle_ok,
        "classification": classification,
        "once_returncode": once_proc.returncode,
        "btc6_shadow_ok": shadow_ok,
        "btc6_new_events": shadow_summary.get("new_events", 0),
        "btc6_open_trades": metrics.get("open_trades", 0),
        "btc6_closed_trades": metrics.get("closed_trades", 0),
        "btc6_total_r": metrics.get("total_r", 0),
        "btc6_total_pips": metrics.get("total_pips", 0),
        "btc6_discord_status": discord_status.get("status", ""),
        "m5_csv": str(resolved["m5"]),
        "m15_csv": str(resolved["m15"]),
        "h4_csv": str(resolved["h4"]),
        "error": error_text,
        "next_run_utc": utc_text(next_run),
        "once_summary_json": str(once_summary_path),
        "shadow_summary_json": str(shadow_summary_path),
        "stdout_log": str(once_stdout),
        "stderr_log": str(once_stderr),
    }
    append_csv(root / "operational_loop_log.csv", row)
    write_json(stable_root / "latest_operational_state.json", {
        "schema_version": "btc_youtube_operational_loop_v2",
        "updated_at_utc": utc_text(),
        "live_files_dir": str(args.files_dir),
        "resolved_live_csvs": {key: str(value) for key, value in resolved.items()},
        "btc6_shadow_lot": 0.01,
        "last_cycle": row,
        "btc6_metrics": metrics,
        "btc6_persistent_trade_ledger": str(args.state_dir / "btc6_shadow_trade_ledger.csv"),
        "btc6_persistent_event_ledger": str(args.state_dir / "btc6_shadow_events.csv"),
    })
    print(
        f"[CYCLE {cycle_index}] ok={cycle_ok} btc6_open={metrics.get('open_trades', 0)} "
        f"btc6_closed={metrics.get('closed_trades', 0)} totalR={metrics.get('total_r', 0)} "
        f"shadow_discord={discord_status.get('status')}",
        flush=True,
    )
    return row, cycle_ok


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operational BTC YouTube loop with persistent BTC6 reference-lot history.")
    parser.add_argument("--files-dir", type=Path, default=DEFAULT_FILES_DIR)
    parser.add_argument("--log-base", type=Path, default=DEFAULT_LOG_BASE)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--interval-minutes", type=int, default=1)
    parser.add_argument("--offset-seconds", type=int, default=10)
    parser.add_argument("--manager-interval-seconds", type=float, default=2.0)
    parser.add_argument("--broker-symbol", default="BTCUSD#")
    parser.add_argument("--expected-login", type=int, default=75539039)
    parser.add_argument("--deviation", type=int, default=100)
    parser.add_argument("--max-symbol-positions", type=int, default=6)
    parser.add_argument("--max-symbol-lot", type=float, default=0.10)
    parser.add_argument("--spread-cost-usd", type=float, default=30.0)
    parser.add_argument("--discord-webhook-url", default="")
    parser.add_argument("--discord-webhook-env", default="DISCORD_WEBHOOK_URL")
    parser.add_argument("--discord-username", default="Mochipoyo BTC YouTube")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--allow-demo-send", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.files_dir = args.files_dir if args.files_dir.is_absolute() else REPO_ROOT / args.files_dir
    args.log_base = args.log_base if args.log_base.is_absolute() else REPO_ROOT / args.log_base
    args.state_dir = args.state_dir if args.state_dir.is_absolute() else REPO_ROOT / args.state_dir
    mkdirp(args.log_base)
    mkdirp(args.state_dir)
    stable_root = stable_log_dir(args.log_base)
    mkdirp(stable_root)

    try:
        resolved = validate_runtime_files(args.files_dir)
    except Exception as exc:
        error_text = traceback.format_exc()
        write_text(stable_root / "latest_startup_error.log", error_text)
        write_json(stable_root / "latest_startup_error.json", {
            "failed_at_utc": utc_text(),
            "error": repr(exc),
            "traceback": error_text,
            "files_dir": str(args.files_dir),
            "available_files": [path.name for path in _available_live_csvs(args.files_dir)],
        })
        print(f"[FATAL] {exc}", flush=True)
        print(f"[FATAL] Full log: {stable_root / 'latest_startup_error.log'}", flush=True)
        return 1

    print("[START] BTC YouTube operational runtime", flush=True)
    print(f"[START] M5 : {resolved['m5']}", flush=True)
    print(f"[START] M15: {resolved['m15']}", flush=True)
    print(f"[START] H4 : {resolved['h4']}", flush=True)
    print(f"[START] Stable logs: {stable_root}", flush=True)

    cycle_index = 0
    last_cycle_ok = True
    try:
        while True:
            cycle_index += 1
            root = week_dir(args.log_base)
            mkdirp(root)
            try:
                row, last_cycle_ok = execute_cycle(args, resolved, cycle_index, root, stable_root)
            except Exception as exc:
                last_cycle_ok = False
                error_text = traceback.format_exc()
                write_text(stable_root / "latest_cycle_error.log", error_text)
                write_json(stable_root / "latest_cycle_error.json", {
                    "failed_at_utc": utc_text(),
                    "cycle_index": cycle_index,
                    "error": repr(exc),
                    "traceback": error_text,
                })
                print(f"[ERROR] Unhandled cycle error: {exc}", flush=True)
                print(f"[ERROR] Full log: {stable_root / 'latest_cycle_error.log'}", flush=True)
                next_run = next_aligned(utc_now(), args.interval_minutes, args.offset_seconds)
                row = {"next_run_utc": utc_text(next_run)}

            if args.max_cycles > 0 and cycle_index >= args.max_cycles:
                return 0 if last_cycle_ok else 1

            next_run_text = str(row.get("next_run_utc", ""))
            try:
                next_run = datetime.strptime(next_run_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            except Exception:
                next_run = next_aligned(utc_now(), args.interval_minutes, args.offset_seconds)
            root = week_dir(args.log_base)
            while utc_now() < next_run:
                run_fast_btc4_manager(args, root, stable_root)
                remaining = (next_run - utc_now()).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(max(0.2, min(float(args.manager_interval_seconds), remaining)))
    except KeyboardInterrupt:
        print("[STOP] Ctrl+C received.", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

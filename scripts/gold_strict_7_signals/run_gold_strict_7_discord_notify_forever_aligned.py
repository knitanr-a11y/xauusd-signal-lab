#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Forever aligned Discord notification loop for GOLD strict 7.

Thin loop. Signal logic lives in run_gold_strict_7_discord_notifier_from_csv.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTIFIER_SCRIPT = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "run_gold_strict_7_discord_notifier_from_csv.py"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_LOOP_OUT_DIR = Path("data/runtime_logs/gold_strict_7_discord_live_loop")
DEFAULT_NOTIFIER_OUT_DIR = Path("data/runtime_logs/gold_strict_7_discord_preview")
DEFAULT_AI_TAG_RULES_JSON = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json")
SCHEMA_VERSION = "gold_strict_7_discord_live_loop_v3_numeric_ai_tags"

SUMMARY_COLUMNS = [
    "loop_started_at", "loop_iteration", "scheduled_for", "started_at", "finished_at", "elapsed_seconds",
    "returncode", "success", "send_discord", "scan_recent_bars", "max_notifications",
    "tail_m5", "tail_h1", "tail_h4", "tail_d1",
    "preview_rows", "ai_tag_hit_rows", "ai_tag_rules_count", "ai_tag_rules_cycle_ok",
    "skipped_duplicates", "ledger_rows_appended", "raw_recent_signals_after_cooldown",
    "ctx_rows", "summary_read_status", "stdout_log", "stderr_log",
]


def now() -> datetime:
    return datetime.now()


def ts_text(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")


def safe_file_ts(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y%m%d_%H%M%S")


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def weekly_dir(base_dir: Path, dt: datetime) -> Path:
    iso = dt.isocalendar()
    return base_dir / f"{dt.year:04d}" / f"{dt.month:02d}" / f"week_{iso.week:02d}"


def append_summary(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in SUMMARY_COLUMNS})


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_notifier_summary(path: Path) -> tuple[str, dict[str, Any]]:
    if not path.exists():
        return "MISSING", {}
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return "OK", obj if isinstance(obj, dict) else {}
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}:{exc}", {}


def next_aligned_time(interval_minutes: int, delay_seconds: int) -> datetime:
    n = now()
    base = n.replace(second=0, microsecond=0)
    next_minute = ((base.minute // interval_minutes) + 1) * interval_minutes
    hour_add = next_minute // 60
    next_minute %= 60
    return base.replace(minute=next_minute) + timedelta(hours=hour_add, seconds=delay_seconds)


def sleep_until(target: datetime) -> None:
    while True:
        remaining = (target - now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 1.0))


def build_notifier_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable, str(NOTIFIER_SCRIPT),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(args.notifier_out_dir),
        "--ai-tag-rules-json", str(args.ai_tag_rules_json),
        "--scan-recent-bars", str(args.scan_recent_bars),
        "--max-notifications", str(args.max_notifications),
        "--bar-offset", str(args.bar_offset),
        "--tail-m5", str(args.tail_m5),
        "--tail-h1", str(args.tail_h1),
        "--tail-h4", str(args.tail_h4),
        "--tail-d1", str(args.tail_d1),
    ]
    cmd.append("--send-discord" if args.send_discord else "--dry-run")
    if args.allow_duplicate:
        cmd.append("--allow-duplicate")
    if args.discord_webhook_url:
        cmd.extend(["--discord-webhook-url", args.discord_webhook_url])
    if args.env_file:
        cmd.extend(["--env-file", str(args.env_file)])
    return cmd


def run_one_iteration(args: argparse.Namespace, *, loop_started_at: str, iteration: int, scheduled_for: datetime, summary_csv: Path, log_dir: Path) -> dict[str, Any]:
    started = now()
    stamp = safe_file_ts(started)
    stdout_log = log_dir / f"gold_strict7_discord_loop_iter_{iteration:06d}_{stamp}.stdout.log"
    stderr_log = log_dir / f"gold_strict7_discord_loop_iter_{iteration:06d}_{stamp}.stderr.log"
    cmd = build_notifier_cmd(args)
    print("=" * 100, flush=True)
    print(f"[{ts_text()}] iteration={iteration} scheduled_for={ts_text(scheduled_for)}", flush=True)
    print("CMD: " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    finished = now()
    write_text(stdout_log, proc.stdout or "")
    write_text(stderr_log, proc.stderr or "")
    summary_status, notifier_summary = read_notifier_summary(resolve_repo_path(args.notifier_out_dir) / "gold_strict_7_discord_preview_summary.json")
    success = proc.returncode == 0 and bool(notifier_summary.get("cycle_ok", False))
    row = {
        "loop_started_at": loop_started_at,
        "loop_iteration": iteration,
        "scheduled_for": ts_text(scheduled_for),
        "started_at": ts_text(started),
        "finished_at": ts_text(finished),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "returncode": int(proc.returncode),
        "success": bool(success),
        "send_discord": bool(args.send_discord),
        "scan_recent_bars": int(args.scan_recent_bars),
        "max_notifications": int(args.max_notifications),
        "tail_m5": int(args.tail_m5),
        "tail_h1": int(args.tail_h1),
        "tail_h4": int(args.tail_h4),
        "tail_d1": int(args.tail_d1),
        "preview_rows": notifier_summary.get("preview_rows", ""),
        "ai_tag_hit_rows": notifier_summary.get("ai_tag_hit_rows", ""),
        "ai_tag_rules_count": notifier_summary.get("ai_tag_rules_count", ""),
        "ai_tag_rules_cycle_ok": notifier_summary.get("ai_tag_rules_cycle_ok", ""),
        "skipped_duplicates": notifier_summary.get("skipped_duplicates", ""),
        "ledger_rows_appended": notifier_summary.get("ledger_rows_appended", ""),
        "raw_recent_signals_after_cooldown": notifier_summary.get("raw_recent_signals_after_cooldown", ""),
        "ctx_rows": notifier_summary.get("ctx_rows", ""),
        "summary_read_status": summary_status,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    append_summary(summary_csv, row)
    print(json.dumps(row, ensure_ascii=False, indent=2, default=str), flush=True)
    if proc.stdout:
        print("--- notifier stdout tail ---", flush=True)
        print("\n".join(proc.stdout.splitlines()[-30:]), flush=True)
    if proc.stderr:
        print("--- notifier stderr ---", flush=True)
        print(proc.stderr, flush=True)
    print("=" * 100, flush=True)
    return row


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Forever aligned loop for GOLD strict 7 Discord notifier.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--loop-out-dir", type=Path, default=DEFAULT_LOOP_OUT_DIR)
    p.add_argument("--notifier-out-dir", type=Path, default=DEFAULT_NOTIFIER_OUT_DIR)
    p.add_argument("--ai-tag-rules-json", type=Path, default=DEFAULT_AI_TAG_RULES_JSON)
    p.add_argument("--env-file", type=Path, default=Path(".env"))
    p.add_argument("--discord-webhook-url", default="")
    p.add_argument("--interval-minutes", type=int, default=5)
    p.add_argument("--run-delay-seconds", type=int, default=2)
    p.add_argument("--scan-recent-bars", type=int, default=36)
    p.add_argument("--tail-m5", type=int, default=2000)
    p.add_argument("--tail-h1", type=int, default=1000)
    p.add_argument("--tail-h4", type=int, default=500)
    p.add_argument("--tail-d1", type=int, default=300)
    p.add_argument("--max-notifications", type=int, default=20)
    p.add_argument("--bar-offset", type=int, default=1)
    p.add_argument("--send-discord", action="store_true")
    p.add_argument("--allow-duplicate", action="store_true")
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--stop-on-error", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0 or 60 % args.interval_minutes != 0:
        raise SystemExit("--interval-minutes must be a positive divisor of 60")
    loop_started_at = ts_text()
    loop_base = weekly_dir(resolve_repo_path(args.loop_out_dir), now())
    log_dir = loop_base / "logs"
    summary_csv = loop_base / "gold_strict_7_discord_live_loop_summary.csv"
    mkdirp(log_dir)
    print("=" * 100, flush=True)
    print("GOLD strict 7 Discord live loop", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"loop_started_at: {loop_started_at}", flush=True)
    print(f"send_discord: {bool(args.send_discord)}", flush=True)
    print(f"run_delay_seconds: {args.run_delay_seconds}", flush=True)
    print(f"ai_tag_rules_json: {args.ai_tag_rules_json}", flush=True)
    print(f"tails: M5={args.tail_m5} H1={args.tail_h1} H4={args.tail_h4} D1={args.tail_d1}", flush=True)
    print(f"csv_dir: {args.csv_dir}", flush=True)
    print(f"summary_csv: {summary_csv}", flush=True)
    print(f"log_dir: {log_dir}", flush=True)
    print("Safety: Discord only. No MT5 order send. No OpenAI call.", flush=True)
    print("=" * 100, flush=True)

    iteration = 0
    if args.run_immediately:
        iteration += 1
        row = run_one_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=now(), summary_csv=summary_csv, log_dir=log_dir)
        if args.stop_on_error and not row.get("success"):
            return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0

    while True:
        scheduled = next_aligned_time(int(args.interval_minutes), int(args.run_delay_seconds))
        print(f"[{ts_text()}] next_run_at={ts_text(scheduled)}", flush=True)
        sleep_until(scheduled)
        iteration += 1
        row = run_one_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=scheduled, summary_csv=summary_csv, log_dir=log_dir)
        if args.stop_on_error and not row.get("success"):
            return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

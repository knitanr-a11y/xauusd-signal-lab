#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILD_SCRIPT = REPO_ROOT / "scripts" / "btc_strict_5_signals" / "run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py"
BUILD_RULES_BAT = REPO_ROOT / "scripts" / "build_btc_strict_5_ai_tag_numeric_rules.bat"
DEFAULT_LOG_BASE = Path("data/runtime_logs/btc")
DEFAULT_STATE_DIR = Path("data/runtime_state/btc/strict_5")
SUMMARY_NAME = "latest_btc_strict_5_official_discord_numeric_ai_tags_loop_result.json"

COLUMNS = [
    "cycle_index", "cycle_start_utc", "cycle_end_utc", "returncode", "cycle_ok", "filter_variant",
    "preview_rows", "message_rows", "ai_tag_hit_rows", "discord_sent_rows", "skipped_duplicates",
    "signals_excluded_by_filter", "ai_tag_rules_count", "d1_used", "next_run_utc",
    "stdout_log", "stderr_log", "summary_json",
]


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


def mkdirp(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def append_csv(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = Path(windows_long_path(path)).exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in COLUMNS})


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def week_dir(base: Path) -> Path:
    d = datetime.now()
    y, w, _ = d.isocalendar()
    return base / f"{y:04d}" / f"{d.month:02d}" / f"week_{w:02d}" / "strict_5_btc" / "official_discord_numeric_ai_tags_loop"


def next_aligned(now: datetime, interval: int, offset: int) -> datetime:
    b = now.replace(second=0, microsecond=0)
    m = ((b.minute // interval) + 1) * interval
    if m >= 60:
        b = b.replace(minute=0) + timedelta(hours=1)
    else:
        b = b.replace(minute=m)
    return b + timedelta(seconds=offset)


def ensure_rules(rule_json: Path, loop_dir: Path) -> bool:
    if rule_json.exists():
        return True
    stdout = loop_dir / "rule_build_stdout.log"
    stderr = loop_dir / "rule_build_stderr.log"
    proc = subprocess.run(["cmd", "/c", str(BUILD_RULES_BAT)], cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    write_text(stdout, proc.stdout or "")
    write_text(stderr, proc.stderr or "")
    return proc.returncode == 0 and rule_json.exists()


def build_cmd(args: argparse.Namespace, out_dir: Path, ledger_csv: Path, rule_json: Path) -> list[str]:
    cmd = [
        sys.executable, str(CHILD_SCRIPT),
        "--filter-variant", args.filter_variant,
        "--ai-tag-rules-json", str(rule_json),
        "--out-dir", str(out_dir),
        "--ledger-csv", str(ledger_csv),
        "--scan-recent-bars", str(args.scan_recent_bars),
        "--max-signal-age-minutes", str(args.max_signal_age_minutes),
        "--max-notifications", str(args.max_notifications),
        "--tail-m15", str(args.tail_m15),
        "--tail-h1", str(args.tail_h1),
        "--tail-h4", str(args.tail_h4),
    ]
    if args.m15_csv:
        cmd += ["--m15-csv", args.m15_csv]
    if args.h1_csv:
        cmd += ["--h1-csv", args.h1_csv]
    if args.h4_csv:
        cmd += ["--h4-csv", args.h4_csv]
    if args.latest_only:
        cmd.append("--latest-only")
    if args.send_discord:
        cmd.append("--send-discord")
    return cmd


def run_cycle(args: argparse.Namespace, i: int, loop_dir: Path, ledger_csv: Path, rule_json: Path) -> dict[str, Any]:
    start = utc_now()
    s = stamp()
    child_out = loop_dir / "child_runs"
    stdout = loop_dir / "cycle_logs" / f"cycle_{i:06d}_{s}_stdout.log"
    stderr = loop_dir / "cycle_logs" / f"cycle_{i:06d}_{s}_stderr.log"
    mkdirp(child_out)
    if not ensure_rules(rule_json, loop_dir):
        row = {"cycle_index": i, "cycle_start_utc": utc_text(start), "cycle_end_utc": utc_text(), "returncode": 2, "cycle_ok": False, "filter_variant": args.filter_variant, "stdout_log": str(stdout), "stderr_log": str(stderr), "summary_json": "RULE_JSON_MISSING"}
        write_text(stdout, "AI tag numeric rules JSON missing and auto-build failed.\n")
        write_text(stderr, "")
        return row
    cmd = build_cmd(args, child_out, ledger_csv, rule_json)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    write_text(stdout, proc.stdout or "")
    write_text(stderr, proc.stderr or "")
    summary_path = child_out / "btc_strict_5_official_numeric_ai_tag_preview_summary.json"
    summary = read_json(summary_path)
    row = {
        "cycle_index": i,
        "cycle_start_utc": utc_text(start),
        "cycle_end_utc": utc_text(),
        "returncode": int(proc.returncode),
        "cycle_ok": bool(proc.returncode == 0 and summary.get("cycle_ok", False)),
        "filter_variant": summary.get("filter_variant", args.filter_variant),
        "preview_rows": summary.get("rows", {}).get("preview_rows", 0),
        "message_rows": summary.get("rows", {}).get("message_rows", 0),
        "ai_tag_hit_rows": summary.get("rows", {}).get("ai_tag_hit_rows", 0),
        "discord_sent_rows": summary.get("discord_sent_rows", 0),
        "skipped_duplicates": summary.get("rows", {}).get("skipped_duplicates", 0),
        "signals_excluded_by_filter": summary.get("rows", {}).get("signals_excluded_by_filter", 0),
        "ai_tag_rules_count": summary.get("ai_tag_rules_count", 0),
        "d1_used": summary.get("d1_used", False),
        "stdout_log": str(stdout),
        "stderr_log": str(stderr),
        "summary_json": str(summary_path),
    }
    print(
        f"[CYCLE {i}] ok={row['cycle_ok']} preview={row['preview_rows']} message={row['message_rows']} "
        f"sent={row['discord_sent_rows']} dup={row['skipped_duplicates']} ai_hit={row['ai_tag_hit_rows']} rules={row['ai_tag_rules_count']}",
        flush=True,
    )
    if not row["cycle_ok"]:
        print("[child stdout tail]", flush=True)
        print("\n".join((proc.stdout or "").splitlines()[-40:]), flush=True)
        print("[child stderr tail]", flush=True)
        print("\n".join((proc.stderr or "").splitlines()[-40:]), flush=True)
    return row


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--log-base", type=Path, default=DEFAULT_LOG_BASE)
    p.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    p.add_argument("--filter-variant", default="buy_h4_context_conservative_v1", choices=["buy_h4_context_conservative_v1", "baseline"])
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--offset-seconds", type=int, default=2)
    p.add_argument("--scan-recent-bars", type=int, default=5)
    p.add_argument("--max-signal-age-minutes", type=int, default=30)
    p.add_argument("--max-notifications", type=int, default=5)
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=2000)
    p.add_argument("--tail-h4", type=int, default=1000)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--send-discord", action="store_true")
    p.add_argument("--max-cycles", type=int, default=0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    base = args.log_base if args.log_base.is_absolute() else REPO_ROOT / args.log_base
    state = args.state_dir if args.state_dir.is_absolute() else REPO_ROOT / args.state_dir
    ledger_csv = state / "official_discord_numeric_ai_tag_ledger.csv"
    rule_json = state / "ai_tag_numeric_rules.json"
    mkdirp(state)
    print(f"BTC strict 5 official Discord numeric AI tags loop variant={args.filter_variant} interval={args.interval_minutes}m +{args.offset_seconds}s ledger={ledger_csv}", flush=True)
    i = 0
    try:
        while True:
            i += 1
            loop_dir = week_dir(base)
            mkdirp(loop_dir)
            row = run_cycle(args, i, loop_dir, ledger_csv, rule_json)
            nxt = next_aligned(utc_now(), args.interval_minutes, args.offset_seconds)
            row["next_run_utc"] = utc_text(nxt)
            loop_csv = loop_dir / "official_discord_numeric_ai_tags_loop_log.csv"
            append_csv(loop_csv, row)
            write_json(loop_dir / SUMMARY_NAME, {"schema_version": "btc_strict_5_official_discord_numeric_ai_tags_loop_v1", "updated_at_utc": utc_text(), "filter_variant": args.filter_variant, "last_cycle": row, "loop_csv": str(loop_csv), "ledger_csv": str(ledger_csv), "rule_json": str(rule_json)})
            if args.max_cycles > 0 and i >= args.max_cycles:
                return 0 if bool(row.get("cycle_ok")) else 1
            time.sleep(max(1.0, (nxt - utc_now()).total_seconds()))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

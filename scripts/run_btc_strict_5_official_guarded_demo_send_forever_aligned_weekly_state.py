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
CHILD_SCRIPT = REPO_ROOT / "scripts" / "btc_strict_5_signals" / "run_btc_strict_5_official_guarded_demo_autotrade_from_csv.py"
DEFAULT_LOG_BASE = Path("data/runtime_logs/btc")
DEFAULT_STATE_DIR = Path("data/runtime_state/btc/strict_5")
DEFAULT_CHILD_OUT_ROOT = Path("data/runtime_logs/btc_strict_5_official_guarded_demo_autotrade")
SUMMARY_NAME = "latest_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state_result.json"
CHILD_SUMMARY_NAME = "latest_btc_strict_5_official_guarded_demo_autotrade_summary.json"
SCHEMA_VERSION = "btc_strict_5_official_loop_v3_gold_aligned_child_logs"

COLUMNS = [
    "cycle_index", "cycle_start_utc", "cycle_end_utc", "returncode", "cycle_ok", "reason",
    "filter_variant", "payload_rows", "signals_excluded_by_official_filter", "sender_sent_rows",
    "sender_order_send_called_count", "d1_used", "tail_m15", "tail_h1", "tail_h4",
    "next_run_utc", "stdout_log", "stderr_log", "summary_json", "child_out_root",
    "child_period_out_dir", "child_root_latest_summary_json", "loop_root_latest_summary_json",
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


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def year_month_dir(base: Path, dt: datetime) -> Path:
    return base / f"{dt.year:04d}" / f"{dt.month:02d}"


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
        return obj if isinstance(obj, dict) else {"cycle_ok": False, "reason": "SUMMARY_JSON_NOT_OBJECT"}
    except Exception as exc:
        return {"cycle_ok": False, "reason": f"SUMMARY_READ_ERROR: {exc}", "summary_json": str(path)}


def append_csv(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = Path(windows_long_path(path)).exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in COLUMNS})


def week_dir(base: Path) -> Path:
    d = datetime.now()
    y, w, _ = d.isocalendar()
    return base / f"{y:04d}" / f"{d.month:02d}" / f"week_{w:02d}" / "strict_5_btc" / "official_guarded_demo_loop"


def next_aligned(now: datetime, interval: int, offset: int) -> datetime:
    b = now.replace(second=0, microsecond=0)
    m = ((b.minute // interval) + 1) * interval
    if m >= 60:
        b = b.replace(minute=0) + timedelta(hours=1)
    else:
        b = b.replace(minute=m)
    return b + timedelta(seconds=offset)


def child_period_out_dir(args: argparse.Namespace, dt: datetime) -> Path:
    child_root = resolve_repo_path(args.child_out_root)
    return year_month_dir(child_root, dt)


def child_root_latest_summary_path(args: argparse.Namespace) -> Path:
    return resolve_repo_path(args.child_out_root) / CHILD_SUMMARY_NAME


def loop_root_latest_summary_path(base: Path) -> Path:
    return base / SUMMARY_NAME


def sync_child_root_latest(args: argparse.Namespace, *, period_summary_path: Path, child_summary: dict[str, Any]) -> Path:
    root_latest = child_root_latest_summary_path(args)
    copied = dict(child_summary)
    copied["root_latest_summary_json"] = str(root_latest)
    copied["period_latest_summary_json"] = str(period_summary_path)
    copied["log_layout"] = {
        "schema_version": SCHEMA_VERSION,
        "child_run_dir_layout": "YYYY/MM/YYYYMMDD_HHMMSS",
        "root_latest_summary_preserved": True,
    }
    write_json(root_latest, copied)
    return root_latest


def build_cmd(args: argparse.Namespace, child_out: Path, ledger: Path) -> list[str]:
    cmd = [
        sys.executable, str(CHILD_SCRIPT),
        "--out-dir", str(child_out),
        "--order-ledger-csv", str(ledger),
        "--filter-variant", args.filter_variant,
        "--scan-recent-bars", str(args.scan_recent_bars),
        "--max-signal-age-minutes", str(args.max_signal_age_minutes),
        "--tail-m15", str(args.tail_m15),
        "--tail-h1", str(args.tail_h1),
        "--tail-h4", str(args.tail_h4),
        "--max-orders", str(args.max_orders),
        "--position-policy", args.position_policy,
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--lot", str(args.lot),
        "--expected-login", str(args.expected_login),
        "--deviation", str(args.deviation),
        "--broker-symbol", args.broker_symbol,
        "--symbol", args.symbol,
    ]
    if args.mql5_files_dir:
        cmd += ["--mql5-files-dir", str(args.mql5_files_dir)]
    if args.m15_csv:
        cmd += ["--m15-csv", args.m15_csv]
    if args.h1_csv:
        cmd += ["--h1-csv", args.h1_csv]
    if args.h4_csv:
        cmd += ["--h4-csv", args.h4_csv]
    if args.latest_only:
        cmd.append("--latest-only")
    if args.terminal_path:
        cmd += ["--terminal-path", args.terminal_path]
    if args.portable:
        cmd.append("--portable")
    if args.send:
        cmd.append("--send")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    return cmd


def run_cycle(args: argparse.Namespace, i: int, loop_dir: Path, ledger: Path) -> dict[str, Any]:
    start = utc_now()
    s = stamp()
    stdout = loop_dir / "cycle_logs" / f"cycle_{i:06d}_{s}_stdout.log"
    stderr = loop_dir / "cycle_logs" / f"cycle_{i:06d}_{s}_stderr.log"
    child_out = child_period_out_dir(args, start)
    mkdirp(child_out)
    cmd = build_cmd(args, child_out, ledger)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    write_text(stdout, proc.stdout or "")
    write_text(stderr, proc.stderr or "")
    period_summary_path = child_out / CHILD_SUMMARY_NAME
    summary = read_json(period_summary_path)
    child_root_latest = child_root_latest_summary_path(args)
    if period_summary_path.exists() and summary.get("summary_json"):
        child_root_latest = sync_child_root_latest(args, period_summary_path=period_summary_path, child_summary=summary)
    row = {
        "cycle_index": i,
        "cycle_start_utc": utc_text(start),
        "cycle_end_utc": utc_text(),
        "returncode": int(proc.returncode),
        "cycle_ok": bool(proc.returncode == 0 and summary.get("cycle_ok")),
        "reason": summary.get("reason", "NO_SUMMARY"),
        "filter_variant": summary.get("filter_variant", args.filter_variant),
        "payload_rows": summary.get("payload_rows", 0),
        "signals_excluded_by_official_filter": summary.get("signals_excluded_by_official_filter", 0),
        "sender_sent_rows": summary.get("sender_sent_rows", 0),
        "sender_order_send_called_count": summary.get("sender_order_send_called_count", 0),
        "d1_used": summary.get("d1_used", False),
        "tail_m15": args.tail_m15,
        "tail_h1": args.tail_h1,
        "tail_h4": args.tail_h4,
        "stdout_log": str(stdout),
        "stderr_log": str(stderr),
        "summary_json": summary.get("summary_json", str(period_summary_path)),
        "child_out_root": str(resolve_repo_path(args.child_out_root)),
        "child_period_out_dir": str(child_out),
        "child_root_latest_summary_json": str(child_root_latest),
    }
    print(
        f"[CYCLE {i}] ok={row['cycle_ok']} reason={row['reason']} variant={row['filter_variant']} "
        f"payload={row['payload_rows']} sent={row['sender_sent_rows']} excluded={row['signals_excluded_by_official_filter']} "
        f"child_out={child_out}",
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
    p.add_argument("--child-out-root", type=Path, default=DEFAULT_CHILD_OUT_ROOT)
    p.add_argument("--filter-variant", default="buy_h4_context_conservative_v1", choices=["buy_h4_context_conservative_v1", "baseline"])
    p.add_argument("--mql5-files-dir", type=Path, default=None)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--offset-seconds", type=int, default=2)
    p.add_argument("--scan-recent-bars", type=int, default=5)
    p.add_argument("--max-signal-age-minutes", type=int, default=30)
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=2000)
    p.add_argument("--tail-h4", type=int, default=1000)
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--position-policy", default="block_any", choices=["block_any", "allow_same_direction", "allow_any_until_max"])
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--symbol", default="BTC")
    p.add_argument("--terminal-path", default="")
    p.add_argument("--portable", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--max-cycles", type=int, default=0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    base = resolve_repo_path(args.log_base)
    state = resolve_repo_path(args.state_dir)
    child_root = resolve_repo_path(args.child_out_root)
    ledger = state / "official_guarded_demo_order_ledger.csv"
    mkdirp(state)
    mkdirp(base)
    mkdirp(child_root)
    print(
        f"BTC strict 5 official loop variant={args.filter_variant} interval={args.interval_minutes}m "
        f"+{args.offset_seconds}s ledger={ledger}",
        flush=True,
    )
    print(f"loop_log_base={base}", flush=True)
    print(f"child_run_layout={child_root}/YYYY/MM/YYYYMMDD_HHMMSS", flush=True)
    print(f"child_root_latest_summary={child_root_latest_summary_path(args)}", flush=True)
    print(f"loop_root_latest_summary={loop_root_latest_summary_path(base)}", flush=True)
    i = 0
    try:
        while True:
            i += 1
            loop_dir = week_dir(base)
            mkdirp(loop_dir)
            row = run_cycle(args, i, loop_dir, ledger)
            nxt = next_aligned(utc_now(), args.interval_minutes, args.offset_seconds)
            row["next_run_utc"] = utc_text(nxt)
            row["loop_root_latest_summary_json"] = str(loop_root_latest_summary_path(base))
            loop_csv = loop_dir / "official_aligned_loop_log.csv"
            append_csv(loop_csv, row)
            latest_loop_summary = {
                "schema_version": SCHEMA_VERSION,
                "updated_at_utc": utc_text(),
                "filter_variant": args.filter_variant,
                "last_cycle": row,
                "loop_csv": str(loop_csv),
                "loop_dir": str(loop_dir),
                "loop_root_latest_summary_json": str(loop_root_latest_summary_path(base)),
                "child_out_root": str(child_root),
                "child_run_dir_layout": "YYYY/MM/YYYYMMDD_HHMMSS",
                "child_root_latest_summary_json": str(child_root_latest_summary_path(args)),
                "persistent_order_ledger_csv": str(ledger),
            }
            write_json(loop_dir / SUMMARY_NAME, latest_loop_summary)
            write_json(loop_root_latest_summary_path(base), latest_loop_summary)
            if args.max_cycles > 0 and i >= args.max_cycles:
                return 0 if bool(row.get("cycle_ok")) else 1
            time.sleep(max(1.0, (nxt - utc_now()).total_seconds()))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

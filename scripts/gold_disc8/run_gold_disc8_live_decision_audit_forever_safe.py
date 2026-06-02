#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Safe wrapper for GOLD DISC8 live decision audit loop.

This wrapper reuses the existing DISC8 candidate detection logic but enforces
operational safety before anything is written to the shared live ledger.

Hard safety rules:
- No OpenAI API call.
- No Discord send.
- No MT5 order_send.
- No SOT mutation.
- No runtime gate rules mutation.
- Operational ledger is append-only with decision_key de-duplication.
- dispatch_ready is forced False unless a future explicit code change is made;
  this script intentionally has no enable-dispatch flag.
- Existing decision_key rows are never appended again.

The old latest CSV remains a current-state snapshot and may be overwritten.
The live decision ledger is the durable append-only record.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT, REPO_ROOT / "scripts"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from run_gold_disc8_live_decision_audit_forever_aligned import (  # noqa: E402
    CANDIDATE_COLUMNS,
    DEFAULT_GATE_RULES_JSON,
    DEFAULT_MANIFEST_JSON,
    DEFAULT_MQL5_FILES_DIR,
    DEFAULT_OUT_DIR,
    LEDGER_COLUMNS,
    LOOP_SUMMARY_COLUMNS,
    NEAR_MISS_COLUMNS,
    STALE_ROW_COLUMNS,
    STRATEGY_DIAGNOSTIC_COLUMNS,
    finalize_strategy_diag,
    load_pre_send_tags,
    parse_manifest,
    read_json,
    scan_candidates,
    ts_text,
    weekly_dir,
    windows_long_path,
    write_csv,
    write_json,
)

SCHEMA_VERSION = "gold_disc8_live_decision_audit_v3_safe_dedup_dispatch_sealed"
SAFE_LOOP_SUMMARY_COLUMNS = LOOP_SUMMARY_COLUMNS + [
    "dispatch_ready_forced_false",
    "dispatch_ready_enabled",
    "duplicate_suppressed_count",
    "new_ledger_rows_appended",
    "existing_ledger_decision_keys",
    "bar_offset_warning",
]


def now() -> datetime:
    return datetime.now()


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def append_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        return
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def read_existing_decision_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    try:
        with open(windows_long_path(path), "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = str(row.get("decision_key", "")).strip()
                if key:
                    keys.add(key)
    except Exception:
        # Ledger corruption should stop the process rather than silently losing de-duplication safety.
        raise RuntimeError(f"Failed to read existing live decision ledger for de-duplication: {path}")
    return keys


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


def force_dispatch_sealed(candidates: list[dict[str, Any]]) -> None:
    for row in candidates:
        row["schema_version"] = SCHEMA_VERSION
        row["dispatch_ready"] = False
        reason = str(row.get("reason", "")).strip()
        seal_note = "dispatch_ready forced false by safe wrapper"
        row["reason"] = f"{reason}; {seal_note}" if reason else seal_note


def dedup_ledger_rows(candidates: list[dict[str, Any]], ledger_csv: Path, iteration: int) -> tuple[list[dict[str, Any]], int, int]:
    existing_keys = read_existing_decision_keys(ledger_csv)
    seen_this_batch: set[str] = set()
    ledger_rows: list[dict[str, Any]] = []
    suppressed = 0
    for row in candidates:
        key = str(row.get("decision_key", "")).strip()
        if not key:
            suppressed += 1
            continue
        if key in existing_keys or key in seen_this_batch:
            suppressed += 1
            continue
        seen_this_batch.add(key)
        lr = dict(row)
        lr["ledger_appended_at"] = ts_text()
        lr["loop_iteration"] = int(iteration)
        ledger_rows.append(lr)
    return ledger_rows, suppressed, len(existing_keys)


def run_iteration(args: argparse.Namespace, *, loop_started_at: str, iteration: int, scheduled_for: datetime, latest_dir: Path, loop_summary_csv: Path) -> dict[str, Any]:
    started = now()
    manifest_json = read_json(args.manifest_json)
    gate_rules = read_json(args.gate_rules_json)
    manifest = parse_manifest(manifest_json)
    tags_by_key = load_pre_send_tags(args.pre_send_tags) if args.pre_send_tags else {}
    candidates, info, diagnostics = scan_candidates(args, manifest, gate_rules, tags_by_key)
    force_dispatch_sealed(candidates)

    candidates_csv = latest_dir / "gold_disc8_live_decision_candidates.csv"
    summary_json = latest_dir / "gold_disc8_live_decision_audit_summary.json"
    strategy_diagnostics_csv = latest_dir / "gold_disc8_live_decision_strategy_diagnostics.csv"
    near_misses_csv = latest_dir / "gold_disc8_live_decision_near_misses.csv"
    stale_rows_csv = latest_dir / "gold_disc8_live_decision_stale_rows.csv"
    ledger_csv = resolve_repo_path(args.out_dir) / "gold_disc8_live_decision_ledger.csv"

    write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
    write_csv(strategy_diagnostics_csv, diagnostics.get("strategy_diagnostics", []), STRATEGY_DIAGNOSTIC_COLUMNS)
    write_csv(near_misses_csv, diagnostics.get("near_misses", []), NEAR_MISS_COLUMNS)
    write_csv(stale_rows_csv, diagnostics.get("stale_rows", []), STALE_ROW_COLUMNS)

    ledger_rows, duplicate_suppressed_count, existing_ledger_keys = dedup_ledger_rows(candidates, ledger_csv, int(iteration))
    append_csv(ledger_csv, ledger_rows, LEDGER_COLUMNS)

    finished = now()
    bar_offset_warning = "OK_CONFIRMED_BAR_MODE" if int(args.bar_offset) >= 1 else "WARNING_BAR_OFFSET_0_MAY_USE_FORMING_BAR"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_SAFE_DEDUP_NO_SEND_NO_ORDER",
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "dispatch_ready_forced_false": True,
        "dispatch_ready_enabled": False,
        "bar_offset_warning": bar_offset_warning,
        "loop_started_at": loop_started_at,
        "loop_iteration": int(iteration),
        "scheduled_for": ts_text(scheduled_for),
        "started_at": ts_text(started),
        "finished_at": ts_text(finished),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "csv_dir": str(args.csv_dir),
        "manifest_json": str(args.manifest_json),
        "gate_rules_json": str(args.gate_rules_json),
        "pre_send_tags": "" if not args.pre_send_tags else str(args.pre_send_tags),
        "scan_recent_bars": int(args.scan_recent_bars),
        "bar_offset": int(args.bar_offset),
        "max_signal_age_minutes": float(args.max_signal_age_minutes),
        "candidates_detected": int(len(candidates)),
        "allow_count": int(sum(1 for r in candidates if r.get("decision") == "ALLOW")),
        "pending_tagger_count": int(sum(1 for r in candidates if r.get("decision") == "PENDING_TAGGER")),
        "block_count": int(sum(1 for r in candidates if r.get("decision") == "BLOCK")),
        "watch_count": int(sum(1 for r in candidates if r.get("decision") == "WATCH_ONLY")),
        "dispatch_ready_count": 0,
        "ledger_rows_appended": int(len(ledger_rows)),
        "new_ledger_rows_appended": int(len(ledger_rows)),
        "duplicate_suppressed_count": int(duplicate_suppressed_count),
        "existing_ledger_decision_keys": int(existing_ledger_keys),
        "candidates_csv": str(candidates_csv),
        "strategy_diagnostics_csv": str(strategy_diagnostics_csv),
        "near_misses_csv": str(near_misses_csv),
        "stale_rows_csv": str(stale_rows_csv),
        "ledger_csv": str(ledger_csv),
        "diagnostic_hint": "latest CSV is current-state snapshot. durable live ledger is append-only and decision_key de-duplicated by safe wrapper.",
        **info,
    }
    write_json(summary_json, summary)
    loop_row = {k: summary.get(k, "") for k in SAFE_LOOP_SUMMARY_COLUMNS}
    loop_row["success"] = True
    loop_row["summary_json"] = str(summary_json)
    loop_row["candidates_csv"] = str(candidates_csv)
    loop_row["strategy_diagnostics_csv"] = str(strategy_diagnostics_csv)
    loop_row["near_misses_csv"] = str(near_misses_csv)
    loop_row["stale_rows_csv"] = str(stale_rows_csv)
    append_csv(loop_summary_csv, [loop_row], SAFE_LOOP_SUMMARY_COLUMNS)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GOLD DISC8 safe live decision audit forever loop.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--gate-rules-json", type=Path, default=DEFAULT_GATE_RULES_JSON)
    p.add_argument("--pre-send-tags", type=Path, default=None, help="Optional validated pre-send tag CSV/JSONL. dispatch_ready remains false in this safe wrapper.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--run-delay-seconds", type=int, default=5)
    p.add_argument("--scan-recent-bars", type=int, default=36)
    p.add_argument("--bar-offset", type=int, default=1)
    p.add_argument("--max-signal-age-minutes", type=float, default=60.0)
    p.add_argument("--mt5-to-local-hours", type=float, default=6.0)
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=800)
    p.add_argument("--tail-d1", type=int, default=500)
    p.add_argument("--max-decisions", type=int, default=50)
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--stop-on-error", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0 or 60 % args.interval_minutes != 0:
        raise SystemExit("--interval-minutes must be a positive divisor of 60")
    loop_started_at = ts_text()
    base_out = resolve_repo_path(args.out_dir)
    latest_dir = base_out / "latest"
    loop_base = weekly_dir(base_out, now())
    loop_summary_csv = loop_base / "gold_disc8_live_decision_loop_summary.csv"
    mkdirp(latest_dir)
    mkdirp(loop_base)
    print("=" * 100, flush=True)
    print("GOLD DISC8 SAFE live decision audit loop", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"loop_started_at: {loop_started_at}", flush=True)
    print(f"csv_dir: {args.csv_dir}", flush=True)
    print(f"manifest_json: {args.manifest_json}", flush=True)
    print(f"gate_rules_json: {args.gate_rules_json}", flush=True)
    print("Safety: audit-only. No Discord send. No MT5 order_send. No OpenAI call.", flush=True)
    print("Ledger safety: append-only with decision_key de-duplication.", flush=True)
    print("Dispatch safety: dispatch_ready is always false in this wrapper.", flush=True)
    print("Bar safety: default bar_offset=1 uses confirmed M15 bar.", flush=True)
    print("=" * 100, flush=True)
    iteration = 0
    if args.run_immediately:
        iteration += 1
        try:
            run_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=now(), latest_dir=latest_dir, loop_summary_csv=loop_summary_csv)
        except Exception as exc:
            print(f"[ERROR] iteration failed: {type(exc).__name__}: {exc}", flush=True)
            if args.stop_on_error:
                return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0
    while True:
        scheduled = next_aligned_time(int(args.interval_minutes), int(args.run_delay_seconds))
        print(f"[{ts_text()}] next_run_at={ts_text(scheduled)}", flush=True)
        sleep_until(scheduled)
        iteration += 1
        try:
            run_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=scheduled, latest_dir=latest_dir, loop_summary_csv=loop_summary_csv)
        except Exception as exc:
            print(f"[ERROR] iteration failed: {type(exc).__name__}: {exc}", flush=True)
            if args.stop_on_error:
                return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

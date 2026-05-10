#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Show compact status for the GOLD multi-strategy aligned dry-run loop.

This script is read-only.

Primary source:

    data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run_aligned/
      latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json

Fallback source:

    data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run_aligned/
      aligned_loop_log.csv

Why fallback exists:
- Older runner versions could overwrite latest summary with cycles_run=0 when
  Ctrl+C happened before the first cycle.
- New runner versions preserve the previous operational summary, but existing
  local files may already contain that stale pre-cycle stop summary.
- The status viewer therefore falls back to the latest valid cycle row in
  aligned_loop_log.csv when the summary has no usable last_cycle.

Safety:
- This script does not run the scanner.
- This script does not send orders.
- This script does not write production registry files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run_aligned")
SUMMARY_NAME = "latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json"
LOOP_LOG_NAME = "aligned_loop_log.csv"


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


def read_json(path: Path) -> dict[str, Any]:
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"summary JSON root is not an object: {path}")
    return obj


def read_latest_valid_loop_csv_row(path: Path) -> dict[str, Any]:
    if not Path(windows_long_path(path)).exists():
        return {}
    latest: dict[str, Any] = {}
    with open(windows_long_path(path), "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            # Prefer an actual completed cycle row. Rows with cycle_index blank/0
            # are not useful as operational status.
            if as_int(row.get("cycle_index"), 0) <= 0:
                continue
            latest = dict(row)
    return latest


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def summary_has_usable_last_cycle(summary: dict[str, Any]) -> bool:
    last = summary.get("last_cycle", {}) if isinstance(summary.get("last_cycle"), dict) else {}
    return bool(
        as_int(summary.get("cycles_run"), 0) > 0
        and as_int(last.get("cycle_index"), 0) > 0
        and last.get("cycle_end_utc", "")
    )


def build_status_from_summary(summary: dict[str, Any], summary_json: Path, out_dir: Path) -> dict[str, Any]:
    last = summary.get("last_cycle", {}) if isinstance(summary.get("last_cycle"), dict) else {}
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}
    outputs = summary.get("outputs", {}) if isinstance(summary.get("outputs"), dict) else {}
    order_send_called_count = as_int(last.get("sender_order_send_called_count"), as_int(safety.get("sender_order_send_called_count"), 0))
    sent_rows = as_int(last.get("sender_sent_rows"), as_int(safety.get("sender_sent_rows"), 0))
    status_ok = bool(
        as_bool(summary.get("loop_ok"), False)
        and as_bool(last.get("cycle_ok"), False)
        and order_send_called_count == 0
        and sent_rows == 0
    )
    return {
        "status_ok": status_ok,
        "status_source": "summary_json",
        "loop_ok": as_bool(summary.get("loop_ok"), False),
        "reason": summary.get("reason", ""),
        "cycles_run": as_int(summary.get("cycles_run"), 0),
        "failed_cycles": as_int(summary.get("failed_cycles"), 0),
        "last_cycle_index": as_int(last.get("cycle_index"), 0),
        "last_cycle_ok": as_bool(last.get("cycle_ok"), False),
        "last_cycle_end_utc": last.get("cycle_end_utc", ""),
        "latest_m15": last.get("latest_confirmed_m15_close_time_fast", ""),
        "same_m15_no_signal_skipped": as_bool(last.get("same_m15_no_signal_skipped"), False),
        "same_m15_skip_reason": last.get("same_m15_skip_reason", ""),
        "signals_found_count": as_int(last.get("signals_found_count"), 0),
        "open_order_intent_count": as_int(last.get("open_order_intent_count"), 0),
        "close_intent_count": as_int(last.get("close_intent_count"), 0),
        "payload_rows_out": as_int(last.get("payload_rows_out"), 0),
        "valid_order_payloads": as_int(last.get("valid_order_payloads"), 0),
        "order_send_called_count": order_send_called_count,
        "sent_rows": sent_rows,
        "next_run_utc": last.get("next_run_utc", ""),
        "stdout_log": last.get("stdout_log", ""),
        "aligned_loop_log_csv": outputs.get("aligned_loop_log_csv", str(out_dir / LOOP_LOG_NAME)),
        "summary_json": str(summary_json),
    }


def build_status_from_loop_csv(row: dict[str, Any], summary_json: Path, loop_csv: Path) -> dict[str, Any]:
    order_send_called_count = as_int(row.get("sender_order_send_called_count"), 0)
    sent_rows = as_int(row.get("sender_sent_rows"), 0)
    cycle_ok = as_bool(row.get("cycle_ok"), False)
    returncode = as_int(row.get("returncode"), 1)
    status_ok = bool(cycle_ok and returncode == 0 and order_send_called_count == 0 and sent_rows == 0)
    return {
        "status_ok": status_ok,
        "status_source": "aligned_loop_log_csv_fallback",
        "loop_ok": status_ok,
        "reason": row.get("reason", ""),
        "cycles_run": as_int(row.get("cycle_index"), 0),
        "failed_cycles": 0 if status_ok else 1,
        "last_cycle_index": as_int(row.get("cycle_index"), 0),
        "last_cycle_ok": cycle_ok,
        "last_cycle_end_utc": row.get("cycle_end_utc", ""),
        "latest_m15": row.get("latest_confirmed_m15_close_time_fast", ""),
        "same_m15_no_signal_skipped": as_bool(row.get("same_m15_no_signal_skipped"), False),
        "same_m15_skip_reason": row.get("same_m15_skip_reason", ""),
        "signals_found_count": as_int(row.get("signals_found_count"), 0),
        "open_order_intent_count": as_int(row.get("open_order_intent_count"), 0),
        "close_intent_count": as_int(row.get("close_intent_count"), 0),
        "payload_rows_out": as_int(row.get("payload_rows_out"), 0),
        "valid_order_payloads": as_int(row.get("valid_order_payloads"), 0),
        "order_send_called_count": order_send_called_count,
        "sent_rows": sent_rows,
        "next_run_utc": row.get("next_run_utc", ""),
        "stdout_log": row.get("stdout_log", ""),
        "aligned_loop_log_csv": str(loop_csv),
        "summary_json": str(summary_json),
        "note": "latest summary had no usable last_cycle; status was recovered from latest valid aligned_loop_log.csv row",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Show latest compact status for GOLD multi-strategy aligned dry-run loop.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--summary-json", type=Path, default=None)
    p.add_argument("--loop-log-csv", type=Path, default=None)
    p.add_argument("--fail-if-no-summary", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--no-csv-fallback", action="store_true", help="Disable fallback to aligned_loop_log.csv when latest summary has no usable last_cycle.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    summary_json = args.summary_json or (args.out_dir / SUMMARY_NAME)
    loop_csv = args.loop_log_csv or (args.out_dir / LOOP_LOG_NAME)
    if not Path(windows_long_path(summary_json)).exists():
        payload = {
            "status_ok": False,
            "status_source": "none",
            "reason": "SUMMARY_JSON_NOT_FOUND",
            "summary_json": str(summary_json),
            "aligned_loop_log_csv": str(loop_csv),
            "hint": "Start scripts\\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat or run one compact test cycle first.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 1 if args.fail_if_no_summary else 0

    summary = read_json(summary_json)
    if summary_has_usable_last_cycle(summary):
        status = build_status_from_summary(summary, summary_json, args.out_dir)
    else:
        fallback_row = {} if args.no_csv_fallback else read_latest_valid_loop_csv_row(loop_csv)
        if fallback_row:
            status = build_status_from_loop_csv(fallback_row, summary_json, loop_csv)
        else:
            # No fallback available; report the summary as-is so the user can see
            # why it is not currently operationally usable.
            status = build_status_from_summary(summary, summary_json, args.out_dir)
            status["status_source"] = "summary_json_no_usable_last_cycle"
            status["note"] = "latest summary has no usable last_cycle and no valid aligned_loop_log.csv fallback row was found"

    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status.get("status_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

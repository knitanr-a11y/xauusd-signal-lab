#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Show compact status for the GOLD multi-strategy aligned dry-run loop.

This script is read-only.

It reads:

    data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run_aligned/
      latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json

and prints only the latest operational status. It does not run the scanner,
does not send orders, and does not write production registry files.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run_aligned")
SUMMARY_NAME = "latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json"


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
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Show latest compact status for GOLD multi-strategy aligned dry-run loop.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--summary-json", type=Path, default=None)
    p.add_argument("--fail-if-no-summary", action=argparse.BooleanOptionalAction, default=False)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    summary_json = args.summary_json or (args.out_dir / SUMMARY_NAME)
    if not Path(windows_long_path(summary_json)).exists():
        payload = {
            "status_ok": False,
            "reason": "SUMMARY_JSON_NOT_FOUND",
            "summary_json": str(summary_json),
            "hint": "Start scripts\\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat or run one compact test cycle first.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 1 if args.fail_if_no_summary else 0

    summary = read_json(summary_json)
    last = summary.get("last_cycle", {}) if isinstance(summary.get("last_cycle"), dict) else {}
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}
    outputs = summary.get("outputs", {}) if isinstance(summary.get("outputs"), dict) else {}

    status_ok = bool(
        as_bool(summary.get("loop_ok"), False)
        and as_bool(last.get("cycle_ok"), False)
        and as_int(last.get("sender_order_send_called_count"), as_int(safety.get("sender_order_send_called_count"), 0)) == 0
        and as_int(last.get("sender_sent_rows"), as_int(safety.get("sender_sent_rows"), 0)) == 0
    )
    status = {
        "status_ok": status_ok,
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
        "order_send_called_count": as_int(last.get("sender_order_send_called_count"), as_int(safety.get("sender_order_send_called_count"), 0)),
        "sent_rows": as_int(last.get("sender_sent_rows"), as_int(safety.get("sender_sent_rows"), 0)),
        "next_run_utc": last.get("next_run_utc", ""),
        "stdout_log": last.get("stdout_log", ""),
        "aligned_loop_log_csv": outputs.get("aligned_loop_log_csv", str(args.out_dir / "aligned_loop_log.csv")),
        "summary_json": str(summary_json),
    }
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

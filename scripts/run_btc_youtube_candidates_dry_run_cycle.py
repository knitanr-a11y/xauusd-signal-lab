#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from btc_youtube_candidate_signals import (  # noqa: E402
    BTC4_ID,
    BTC5_ID,
    BTC6_ID,
    NOTIFICATION_COLUMNS,
    ORDER_COLUMNS,
    detect_youtube_candidates,
    validate_order_group,
)

DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/btc_youtube_candidates_dry_run_cycle")
SUMMARY_NAME = "latest_btc_youtube_candidates_dry_run_cycle_result.json"
MAX_SIGNAL_AGE_MINUTES = 20


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


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_csv(frame: pd.DataFrame, path: Path, columns: list[str]) -> None:
    mkdirp(path.parent)
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    frame.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def resolve_csv(csv_dir: Path, explicit: str, filename: str) -> Path:
    return Path(explicit) if explicit else csv_dir / filename


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def filter_fresh(frame: pd.DataFrame, *, max_age_minutes: int = MAX_SIGNAL_AGE_MINUTES, now_utc: pd.Timestamp | None = None) -> pd.DataFrame:
    if frame.empty or "entry_time" not in frame.columns:
        return frame.copy()
    now = now_utc if now_utc is not None else pd.Timestamp.now(tz="UTC")
    if now.tzinfo is not None:
        now = now.tz_convert("UTC").tz_localize(None)
    entries = pd.to_datetime(frame["entry_time"], errors="coerce", utc=True).dt.tz_convert(None)
    age_minutes = (now - entries).dt.total_seconds() / 60.0
    mask = entries.notna() & age_minutes.between(-2.0, float(max_age_minutes), inclusive="both")
    return frame.loc[mask].copy().reset_index(drop=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect YouTube-derived BTC4/5/6 candidates. No Discord or MT5 calls.")
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--m5-csv", default="")
    parser.add_argument("--m15-csv", default="")
    parser.add_argument("--h4-csv", default="")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    mkdirp(args.out_dir)
    paths = {
        "m5_csv": resolve_csv(args.csv_dir, args.m5_csv, "btcusdsharp_m5.csv"),
        "m15_csv": resolve_csv(args.csv_dir, args.m15_csv, "btcusdsharp_m15.csv"),
        "h4_csv": resolve_csv(args.csv_dir, args.h4_csv, "btcusdsharp_h4.csv"),
        "notification_candidates_csv": args.out_dir / "candidates" / "btc_youtube_notification_candidates.csv",
        "trade_notification_candidates_csv": args.out_dir / "candidates" / "btc_youtube_trade_notification_candidates.csv",
        "monitor_notification_candidates_csv": args.out_dir / "candidates" / "btc_youtube_monitor_notification_candidates.csv",
        "order_payloads_csv": args.out_dir / "payload" / "order_payloads.csv",
        "summary_json": args.out_dir / SUMMARY_NAME,
    }
    try:
        result = detect_youtube_candidates(
            m5_csv=paths["m5_csv"], m15_csv=paths["m15_csv"], h4_csv=paths["h4_csv"]
        )
        raw_notifications = result.notification_candidates
        notifications = filter_fresh(raw_notifications)
        trade_notifications = notifications[notifications["trade_enabled"].astype(bool)].copy() if not notifications.empty else pd.DataFrame(columns=NOTIFICATION_COLUMNS)
        monitor_notifications = notifications[~notifications["trade_enabled"].astype(bool)].copy() if not notifications.empty else pd.DataFrame(columns=NOTIFICATION_COLUMNS)
        fresh_signal_keys = set(trade_notifications.get("signal_key", pd.Series(dtype=str)).astype(str))
        raw_orders = result.order_payloads
        orders = raw_orders[raw_orders.get("parent_signal_key", pd.Series(dtype=str)).astype(str).isin(fresh_signal_keys)].copy() if not raw_orders.empty else raw_orders
        stale_filtered = {
            "notifications": int(len(raw_notifications) - len(notifications)),
            "order_payloads": int(len(raw_orders) - len(orders)),
        }
        validation_errors = validate_order_group(orders)
        cycle_ok = not validation_errors
        reason = "BTC_YOUTUBE_DRY_RUN_PASS" if cycle_ok else "BTC_YOUTUBE_ORDER_CONTRACT_FAILED"
        error = "" if cycle_ok else "; ".join(validation_errors)
    except Exception as exc:
        notifications = pd.DataFrame(columns=NOTIFICATION_COLUMNS)
        trade_notifications = pd.DataFrame(columns=NOTIFICATION_COLUMNS)
        monitor_notifications = pd.DataFrame(columns=NOTIFICATION_COLUMNS)
        orders = pd.DataFrame(columns=ORDER_COLUMNS)
        result = None
        stale_filtered = {"notifications": 0, "order_payloads": 0}
        validation_errors = [repr(exc)]
        cycle_ok = False
        reason = "BTC_YOUTUBE_DRY_RUN_FAILED"
        error = repr(exc)

    write_csv(notifications, paths["notification_candidates_csv"], NOTIFICATION_COLUMNS)
    write_csv(trade_notifications, paths["trade_notification_candidates_csv"], NOTIFICATION_COLUMNS)
    write_csv(monitor_notifications, paths["monitor_notification_candidates_csv"], NOTIFICATION_COLUMNS)
    write_csv(orders, paths["order_payloads_csv"], ORDER_COLUMNS)

    summary = {
        "schema_version": "btc_youtube_candidates_dry_run_v1",
        "cycle_at_utc": utc_text(),
        "cycle_ok": bool(cycle_ok),
        "reason": reason,
        "error": error,
        "candidates": {
            BTC4_ID: {"discord": True, "demo_order": True, "lot": 0.02, "split": "0.01 TP1 + 0.01 TP2"},
            BTC5_ID: {"discord": True, "demo_order": True, "lot": 0.01},
            BTC6_ID: {"discord": True, "demo_order": False, "mode": "MONITOR_ONLY"},
        },
        "rows": {
            "notification_candidates": int(len(notifications)),
            "trade_notification_candidates": int(len(trade_notifications)),
            "monitor_notification_candidates": int(len(monitor_notifications)),
            "order_payloads": int(len(orders)),
        },
        "candidate_counts": {} if result is None else result.counts,
        "max_signal_age_minutes": MAX_SIGNAL_AGE_MINUTES,
        "stale_rows_filtered": stale_filtered,
        "latest_closed": {} if result is None else result.latest_closed,
        "synthetic_entry_times": {} if result is None else result.synthetic_entry_times,
        "order_contract_errors": validation_errors,
        "safety": {
            "discord_called": False,
            "mt5_called": False,
            "order_send_called": False,
            "state_mutated": False,
            "closed_bar_inputs_only": True,
            "synthetic_row_contains_no_future_high_low": True,
            "btc6_order_payload_forbidden": True,
        },
        "paths": {key: str(value) for key, value in paths.items()},
    }
    write_json(paths["summary_json"], summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if summary["cycle_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

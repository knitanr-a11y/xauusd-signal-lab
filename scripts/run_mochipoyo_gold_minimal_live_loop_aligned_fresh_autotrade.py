#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aligned Mochipoyo GOLD live loop with auto-trade execution guards.

This wrapper intentionally keeps the existing validated Mochipoyo live flow
unchanged up to Discord/notification-ledger processing, then applies two guards
only around MT5 auto-trade execution.

Guard 1: stale signal auto-trade filter
- The notification flow may legitimately catch up delayed, unnotified signals
  after a loop restart.
- That is acceptable for Discord notification, but unsafe for market orders.
- For auto-trade payload generation, keep only rows where
    latest_trigger_close_time - signal_close_time <= max_age_minutes.
- Times are compared in the MT5/server timestamp domain by using the loop's own
  pair_trigger_to_scan.csv, not the Windows local clock.
- Stale rows are written to order/auto_trade_stale_signal_rows.csv for audit.
- Notification ledger and Discord send behavior are not changed by this guard.

Guard 2: market-closed deferral
- MT5 can return retcode=10018 / comment=Market closed from order_send.
- That is an execution-window condition, not a corrupted scanner/loop state.
- This wrapper normalizes that specific outcome to DEFERRED_MARKET_CLOSED with
  auto_trade_returncode=0 so --stop-on-error does not stop the forever loop.
- The sender report and order ledger still contain the original ERROR_ORDER_SEND
  row for audit until the sender duplicate-ledger policy is fixed separately.

Default max age is 20 minutes, suitable for an M15-close loop. Use
--auto-trade-max-signal-age-minutes to tune it. A value <= 0 disables the stale
signal guard.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_mochipoyo_gold_minimal_live_loop_aligned as aligned  # noqa: E402

MT5_RETCODE_MARKET_CLOSED = 10018


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


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(windows_long_path(p), "r", encoding="utf-8-sig") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def extract_wrapper_args(argv: list[str]) -> tuple[float, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--auto-trade-max-signal-age-minutes",
        type=float,
        default=20.0,
        help="Maximum signal age, in MT5/server minutes, allowed for auto-trade payload generation. <=0 disables.",
    )
    parsed, remaining = parser.parse_known_args(argv)
    return float(parsed.auto_trade_max_signal_age_minutes), remaining


def _status_payload(status: str, *, max_age_minutes: float, before_rows: int = 0, kept_rows: int = 0, stale_rows: int = 0, reason: str = "") -> dict[str, Any]:
    return {
        "auto_trade_freshness_filter_status": status,
        "auto_trade_freshness_max_age_minutes": float(max_age_minutes),
        "auto_trade_freshness_rows_before": int(before_rows),
        "auto_trade_freshness_rows_kept": int(kept_rows),
        "auto_trade_freshness_stale_rows": int(stale_rows),
        "auto_trade_freshness_reason": reason,
    }


def _latest_close_lookup(iteration_dir: Path) -> dict[str, pd.Timestamp]:
    path = iteration_dir / "pair_trigger_to_scan.csv"
    if not path.exists():
        return {}
    try:
        df = read_csv(path)
    except Exception:
        return {}
    if df.empty or "latest_close_time" not in df.columns:
        return {}
    lookup: dict[str, pd.Timestamp] = {}
    for _, row in df.iterrows():
        latest = pd.to_datetime(row.get("latest_close_time"), errors="coerce")
        if pd.isna(latest):
            continue
        pair = str(row.get("pair_name", "")).strip().upper()
        if pair:
            lookup[pair] = pd.Timestamp(latest)
    return lookup


def _fallback_latest_close(latest_by_pair: dict[str, pd.Timestamp]) -> pd.Timestamp | None:
    if not latest_by_pair:
        return None
    return max(latest_by_pair.values())


def apply_auto_trade_freshness_filter(iteration_dir: Path, *, max_age_minutes: float) -> dict[str, Any]:
    """Filter notification_ledger_to_send.csv before order payload generation.

    The file is intentionally modified in-place only under the per-iteration
    output directory, after notification/Discord handling has already completed.
    Persistent notification ledger files are not touched here.
    """
    ledger_dir = iteration_dir / "ledger"
    order_dir = iteration_dir / "order"
    order_dir.mkdir(parents=True, exist_ok=True)
    to_send_csv = ledger_dir / "notification_ledger_to_send.csv"

    if max_age_minutes <= 0:
        return _status_payload("DISABLED", max_age_minutes=max_age_minutes, reason="max_age_minutes <= 0")
    if not to_send_csv.exists():
        return _status_payload("SKIPPED_NO_TO_SEND_CSV", max_age_minutes=max_age_minutes, reason=str(to_send_csv))

    try:
        df = read_csv(to_send_csv)
    except Exception as exc:
        return _status_payload("ERROR_READ_TO_SEND_CSV", max_age_minutes=max_age_minutes, reason=repr(exc))
    before_rows = int(len(df))
    if df.empty:
        return _status_payload("OK_EMPTY", max_age_minutes=max_age_minutes, before_rows=0, kept_rows=0, stale_rows=0)
    if "signal_close_time" not in df.columns:
        # Fail closed for auto-trade freshness: no timestamp means no market order.
        backup = order_dir / "notification_ledger_to_send_before_auto_trade_freshness.csv"
        write_csv(df, backup)
        stale = df.copy()
        stale["auto_trade_freshness_status"] = "STALE_OR_UNKNOWN"
        stale["auto_trade_freshness_reason"] = "missing signal_close_time column"
        write_csv(stale, order_dir / "auto_trade_stale_signal_rows.csv")
        write_csv(df.iloc[0:0].copy(), to_send_csv)
        return _status_payload(
            "FILTERED_ALL_MISSING_SIGNAL_CLOSE_TIME",
            max_age_minutes=max_age_minutes,
            before_rows=before_rows,
            kept_rows=0,
            stale_rows=before_rows,
            reason="missing signal_close_time column",
        )

    latest_by_pair = _latest_close_lookup(iteration_dir)
    fallback_latest = _fallback_latest_close(latest_by_pair)
    if fallback_latest is None:
        backup = order_dir / "notification_ledger_to_send_before_auto_trade_freshness.csv"
        write_csv(df, backup)
        stale = df.copy()
        stale["auto_trade_freshness_status"] = "STALE_OR_UNKNOWN"
        stale["auto_trade_freshness_reason"] = "missing pair_trigger_to_scan latest_close_time"
        write_csv(stale, order_dir / "auto_trade_stale_signal_rows.csv")
        write_csv(df.iloc[0:0].copy(), to_send_csv)
        return _status_payload(
            "FILTERED_ALL_MISSING_LATEST_CLOSE_TIME",
            max_age_minutes=max_age_minutes,
            before_rows=before_rows,
            kept_rows=0,
            stale_rows=before_rows,
            reason="missing latest close time for MT5-domain freshness comparison",
        )

    work = df.copy()
    work["_signal_close_time_dt"] = pd.to_datetime(work["signal_close_time"], errors="coerce")
    effective_latest: list[pd.Timestamp] = []
    for _, row in work.iterrows():
        pair = str(row.get("pair_name", "")).strip().upper()
        effective_latest.append(latest_by_pair.get(pair, fallback_latest))
    work["_latest_close_time_dt"] = effective_latest
    work["auto_trade_signal_age_minutes"] = (
        (work["_latest_close_time_dt"] - work["_signal_close_time_dt"]).dt.total_seconds() / 60.0
    )

    valid_age = work["auto_trade_signal_age_minutes"].notna() & (work["auto_trade_signal_age_minutes"] >= 0)
    fresh = valid_age & (work["auto_trade_signal_age_minutes"] <= float(max_age_minutes))
    kept = work.loc[fresh].copy()
    stale = work.loc[~fresh].copy()

    def _cleanup(out: pd.DataFrame) -> pd.DataFrame:
        return out.drop(columns=["_signal_close_time_dt", "_latest_close_time_dt"], errors="ignore")

    backup = order_dir / "notification_ledger_to_send_before_auto_trade_freshness.csv"
    write_csv(df, backup)
    write_csv(_cleanup(kept), to_send_csv)
    write_csv(_cleanup(stale), order_dir / "auto_trade_stale_signal_rows.csv")

    status = "OK_ALL_FRESH" if stale.empty else ("FILTERED_ALL_STALE" if kept.empty else "FILTERED_SOME_STALE")
    return _status_payload(
        status,
        max_age_minutes=max_age_minutes,
        before_rows=before_rows,
        kept_rows=int(len(kept)),
        stale_rows=int(len(stale)),
        reason="latest_trigger_close_time - signal_close_time freshness guard for auto-trade",
    )


def _clean_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return int(default)
        if pd.isna(value):
            return int(default)
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _result_is_market_closed(row: dict[str, Any]) -> bool:
    retcode = _clean_int(row.get("order_send_retcode"), default=-1)
    comment = str(row.get("order_send_comment", "")).strip().lower()
    errors = str(row.get("validation_errors", "")).strip().lower()
    return retcode == MT5_RETCODE_MARKET_CLOSED or "market closed" in comment or "market closed" in errors


def _market_closed_report(report: dict[str, Any]) -> bool:
    if not report:
        return False
    rows_out = _clean_int(report.get("rows_out"), 0)
    sent_rows = _clean_int(report.get("sent_rows"), 0)
    error_rows = _clean_int(report.get("error_rows"), 0)
    called = _clean_int(report.get("order_send_called_count"), 0)
    results = report.get("results", [])
    if rows_out <= 0 or called <= 0 or sent_rows != 0 or error_rows <= 0:
        return False
    if not isinstance(results, list) or not results:
        return False
    error_like_rows: list[dict[str, Any]] = []
    for item in results:
        if isinstance(item, dict):
            status = str(item.get("order_status", "")).upper()
            send_ok = str(item.get("order_send_ok", "")).strip().lower() in {"true", "1", "yes", "y"}
            if not send_ok and ("ERROR" in status or _clean_int(item.get("order_send_retcode"), 0) != 0):
                error_like_rows.append(item)
    if not error_like_rows:
        return False
    return all(_result_is_market_closed(row) for row in error_like_rows)


def _write_deferred_marker(iteration_dir: Path, report: dict[str, Any]) -> None:
    marker = {
        "schema_version": "mochipoyo_auto_trade_deferred_market_closed_v1",
        "deferred_status": "DEFERRED_MARKET_CLOSED",
        "reason": "MT5 order_send returned retcode=10018 / Market closed. Loop continues; no order was sent.",
        "rows_out": _clean_int(report.get("rows_out"), 0),
        "order_send_called_count": _clean_int(report.get("order_send_called_count"), 0),
        "sent_rows": _clean_int(report.get("sent_rows"), 0),
        "error_rows": _clean_int(report.get("error_rows"), 0),
        "input_csv": report.get("input_csv", ""),
        "order_ledger_csv": report.get("order_ledger_csv", ""),
    }
    write_json(iteration_dir / "auto_trade" / "deferred_market_closed.json", marker)


def install_patch(max_age_minutes: float) -> None:
    original_order_payload_stage = aligned.base.run_order_payload_stage
    original_auto_trade_stage = aligned.base.run_auto_trade_stage

    def patched_run_order_payload_stage(args: argparse.Namespace, iteration_dir: Path, once_event: dict[str, Any] | None = None) -> dict[str, Any]:
        auto_trade_enabled = bool(getattr(args, "enable_auto_trade_send", False) or getattr(args, "enable_auto_trade_dry_run", False))
        if auto_trade_enabled:
            freshness_event = apply_auto_trade_freshness_filter(Path(iteration_dir), max_age_minutes=max_age_minutes)
        else:
            freshness_event = _status_payload(
                "SKIPPED_AUTO_TRADE_DISABLED",
                max_age_minutes=max_age_minutes,
                reason="auto-trade stage is disabled",
            )
        order_event = original_order_payload_stage(args, iteration_dir, once_event)
        return {**order_event, **freshness_event}

    def patched_run_auto_trade_stage(args: argparse.Namespace, iteration_dir: Path, order_event: dict[str, Any]) -> dict[str, Any]:
        auto_event = original_auto_trade_stage(args, iteration_dir, order_event)
        send_enabled = bool(getattr(args, "enable_auto_trade_send", False))
        if not send_enabled:
            return auto_event
        if str(auto_event.get("auto_trade_status", "")).upper() != "ERROR":
            return auto_event
        report = read_json(Path(iteration_dir) / "auto_trade" / "mt5_order_send_report.json")
        if not _market_closed_report(report):
            return auto_event
        _write_deferred_marker(Path(iteration_dir), report)
        normalized = dict(auto_event)
        normalized["auto_trade_status"] = "DEFERRED_MARKET_CLOSED"
        normalized["auto_trade_returncode"] = 0
        normalized["auto_trade_deferred"] = True
        normalized["auto_trade_deferred_reason"] = "MT5 order_send retcode=10018 / Market closed"
        normalized["auto_trade_market_closed_rows"] = _clean_int(report.get("error_rows"), 0)
        return normalized

    aligned.base.run_order_payload_stage = patched_run_order_payload_stage
    aligned.base.run_auto_trade_stage = patched_run_auto_trade_stage


def main() -> int:
    max_age_minutes, remaining = extract_wrapper_args(sys.argv[1:])
    sys.argv = [sys.argv[0]] + remaining
    install_patch(max_age_minutes)
    print("run_mochipoyo_gold_minimal_live_loop_aligned_fresh_autotrade")
    print(f"auto_trade_max_signal_age_minutes: {max_age_minutes}")
    print("market_closed_deferral: enabled")
    return int(aligned.main())


if __name__ == "__main__":
    raise SystemExit(main())

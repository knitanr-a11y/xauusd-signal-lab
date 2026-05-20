#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build BTC strict-5 signal preview CSV from MT5 candle CSVs.

Research / preview only.

No Discord send.
No MT5 call.
No order_send.
No OpenAI call.
No runtime ledger mutation.
No D1 read or D1 condition.

This script intentionally imports the same spec and detection functions used by
run_btc_strict_5_backtest_from_csv.py so the preview path cannot silently drift
from the backtest path.

Important live-preview note:
- The backtest enters at the next M15 open after a confirmed signal candle.
- In live CSV preview, the next M15 open may not be present yet.
- Therefore this script outputs signal-preview fields and TP/SL distances. Any
  later guarded order payload builder must compute actual execution-price based
  SL/TP from live bid/ask or a separately approved execution reference.
"""
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

from btc_strict_5_signal_specs import (  # noqa: E402
    DEFAULT_BROKER_SYMBOL,
    DEFAULT_SYMBOL,
    get_signal_specs,
    validate_signal_specs,
)
from run_btc_strict_5_backtest_from_csv import (  # noqa: E402
    BTC_PIP_SIZE,
    DEFAULT_MQL5_FILES_DIR,
    add_indicators,
    choose_path,
    detect_signals,
    join_confirmed_context,
    read_ohlc_csv,
    time_text,
    windows_long_path,
    write_csv,
    write_json,
)

SCHEMA_VERSION = "btc_strict_5_preview_v1"
DEFAULT_OUT_DIR = Path("data/research_results/btc_strict_5_signal_candidates")
PREVIEW_COLUMNS = [
    "created_at_utc",
    "schema_version",
    "preview_id",
    "signal_id",
    "strategy_id",
    "candidate_base",
    "candidate_family",
    "direction",
    "broker_symbol",
    "symbol",
    "trigger_timeframe",
    "signal_time",
    "base_close_time",
    "entry_time",
    "entry_reference_policy",
    "signal_close_price",
    "next_m15_open_available",
    "next_m15_open_price",
    "tp_price_distance",
    "sl_price_distance",
    "tp_pips",
    "sl_pips",
    "rr",
    "horizon_m15",
    "horizon_minutes",
    "h1_time",
    "h1_close_time",
    "h1_confirmed_ok",
    "h1_close_lag_minutes",
    "h4_time",
    "h4_close_time",
    "h4_confirmed_ok",
    "h4_close_lag_minutes",
    "strict_no_future_ok",
    "d1_used",
    "trigger_hour",
    "trigger_close_pos",
    "trigger_range_atr14",
    "trigger_body_atr14",
    "trigger_atr14",
    "trigger_bb_width",
    "trigger_rsi14",
    "trigger_cci20",
    "trigger_macd_hist",
    "trigger_macd_delta",
    "trigger_ema200_slope3",
    "h1_macd_hist",
    "h1_ema20_slope3",
    "h4_ema20",
    "h4_ema50",
    "reason",
]


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def id_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "NA"
    return pd.Timestamp(ts).strftime("%Y%m%d_%H%M")


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def build_m15_next_open_lookup(m15: pd.DataFrame) -> dict[pd.Timestamp, float]:
    lookup: dict[pd.Timestamp, float] = {}
    if m15.empty:
        return lookup
    for _, row in m15.iterrows():
        lookup[pd.Timestamp(row["time"])] = float(row["open"])
    return lookup


def build_preview_rows(
    *,
    signals: pd.DataFrame,
    ctx: pd.DataFrame,
    m15_next_open_lookup: dict[pd.Timestamp, float],
    broker_symbol: str,
    symbol: str,
) -> pd.DataFrame:
    specs = {spec.strategy_id: spec for spec in get_signal_specs()}
    ctx_by_time = {pd.Timestamp(row["time"]): row for _, row in ctx.iterrows()}
    rows: list[dict[str, Any]] = []
    now = utc_now_text()
    for _, sig in signals.iterrows():
        spec = specs[str(sig["strategy_id"])]
        signal_time = pd.Timestamp(sig["signal_time"])
        entry_time = pd.Timestamp(sig["entry_time"])
        ctx_row = ctx_by_time.get(signal_time)
        signal_close = safe_float(ctx_row.get("close") if ctx_row is not None else None)
        next_open = m15_next_open_lookup.get(entry_time)
        rows.append({
            "created_at_utc": now,
            "schema_version": SCHEMA_VERSION,
            "preview_id": f"{spec.strategy_id}_{id_time_text(signal_time)}_PREVIEW",
            "signal_id": sig.get("signal_id", ""),
            "strategy_id": spec.strategy_id,
            "candidate_base": spec.candidate_base,
            "candidate_family": spec.family,
            "direction": spec.direction,
            "broker_symbol": broker_symbol,
            "symbol": symbol,
            "trigger_timeframe": "M15",
            "signal_time": time_text(signal_time),
            "base_close_time": time_text(sig.get("base_close_time")),
            "entry_time": time_text(entry_time),
            "entry_reference_policy": "NEXT_M15_OPEN_IF_AVAILABLE_ELSE_SIGNAL_CLOSE_PREVIEW_ONLY",
            "signal_close_price": signal_close,
            "next_m15_open_available": next_open is not None,
            "next_m15_open_price": next_open if next_open is not None else "",
            "tp_price_distance": spec.tp_price_distance,
            "sl_price_distance": spec.sl_price_distance,
            "tp_pips": spec.tp_pips,
            "sl_pips": spec.sl_pips,
            "rr": spec.rr,
            "horizon_m15": spec.horizon_m15,
            "horizon_minutes": spec.horizon_minutes,
            "h1_time": time_text(sig.get("h1_time")),
            "h1_close_time": time_text(sig.get("h1_close_time")),
            "h1_confirmed_ok": bool(sig.get("h1_confirmed_ok", False)),
            "h1_close_lag_minutes": sig.get("h1_close_lag_minutes"),
            "h4_time": time_text(sig.get("h4_time")),
            "h4_close_time": time_text(sig.get("h4_close_time")),
            "h4_confirmed_ok": bool(sig.get("h4_confirmed_ok", False)),
            "h4_close_lag_minutes": sig.get("h4_close_lag_minutes"),
            "strict_no_future_ok": bool(sig.get("strict_no_future_ok", False)),
            "d1_used": False,
            "trigger_hour": sig.get("trigger_hour"),
            "trigger_close_pos": sig.get("trigger_close_pos"),
            "trigger_range_atr14": sig.get("trigger_range_atr14"),
            "trigger_body_atr14": sig.get("trigger_body_atr14"),
            "trigger_atr14": sig.get("trigger_atr14"),
            "trigger_bb_width": sig.get("trigger_bb_width"),
            "trigger_rsi14": sig.get("trigger_rsi14"),
            "trigger_cci20": sig.get("trigger_cci20"),
            "trigger_macd_hist": sig.get("trigger_macd_hist"),
            "trigger_macd_delta": sig.get("trigger_macd_delta"),
            "trigger_ema200_slope3": sig.get("trigger_ema200_slope3"),
            "h1_macd_hist": sig.get("h1_macd_hist"),
            "h1_ema20_slope3": sig.get("h1_ema20_slope3"),
            "h4_ema20": sig.get("h4_ema20"),
            "h4_ema50": sig.get("h4_ema50"),
            "reason": sig.get("reason", ""),
        })
    return pd.DataFrame(rows, columns=PREVIEW_COLUMNS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build BTC strict 5 signal preview CSV. No Discord/MT5/order/API calls.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--preview-csv", default="", help="Optional explicit output CSV path.")
    p.add_argument("--summary-json", default="", help="Optional explicit output JSON path.")
    p.add_argument("--scan-recent-bars", type=int, default=500, help="Only preview signals whose M15 signal row is inside the latest N M15 rows. 0 = all.")
    p.add_argument("--latest-only", action="store_true", help="Keep only the latest preview row after all filters.")
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    return p.parse_args()


def choose_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    csv_path = Path(args.preview_csv) if args.preview_csv else args.out_dir / "btc_strict_5_signal_preview.csv"
    json_path = Path(args.summary_json) if args.summary_json else args.out_dir / "btc_strict_5_signal_preview_summary.json"
    return csv_path, json_path


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    input_paths = {
        "m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file),
        "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file),
        "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file),
    }
    preview_csv, summary_json = choose_output_paths(args)

    print("BTC strict 5 preview from CSV")
    print("research_preview_only=true")
    print("d1_csv=NOT_USED d1_used=false")
    for key, value in input_paths.items():
        print(f"{key}_csv={value}")

    m15 = add_indicators(read_ohlc_csv(input_paths["m15"]), include_donchian=True)
    h1 = add_indicators(read_ohlc_csv(input_paths["h1"]))
    h4 = add_indicators(read_ohlc_csv(input_paths["h4"]))
    ctx = join_confirmed_context(m15, h1, h4)
    signals = detect_signals(ctx, get_signal_specs())

    if args.scan_recent_bars and int(args.scan_recent_bars) > 0 and not ctx.empty:
        cutoff_time = pd.Timestamp(ctx.iloc[max(0, len(ctx) - int(args.scan_recent_bars))]["time"])
        signals = signals[pd.to_datetime(signals["signal_time"]) >= cutoff_time].copy() if not signals.empty else signals
    if args.latest_only and not signals.empty:
        signals = signals.sort_values(["signal_time", "strategy_id"]).tail(1).copy()

    preview = build_preview_rows(
        signals=signals,
        ctx=ctx,
        m15_next_open_lookup=build_m15_next_open_lookup(m15),
        broker_symbol=str(args.broker_symbol),
        symbol=str(args.symbol),
    )
    write_csv(preview, preview_csv)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "research_preview_only": True,
        "orders_sent": False,
        "discord_sent": False,
        "openai_called": False,
        "runtime_ledger_mutated": False,
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "input_paths": {k: str(v) for k, v in input_paths.items()},
        "outputs": {"preview_csv": str(preview_csv)},
        "scan_recent_bars": int(args.scan_recent_bars),
        "latest_only": bool(args.latest_only),
        "rows": {
            "m15": int(len(m15)),
            "h1": int(len(h1)),
            "h4": int(len(h4)),
            "raw_signals_after_recent_filter": int(len(signals)),
            "preview_rows": int(len(preview)),
        },
        "audit": {
            "strict_no_future_ng_rows": int((~preview["strict_no_future_ok"].astype(bool)).sum()) if not preview.empty else 0,
            "h1_confirmed_ng_rows": int((~preview["h1_confirmed_ok"].astype(bool)).sum()) if not preview.empty else 0,
            "h4_confirmed_ng_rows": int((~preview["h4_confirmed_ok"].astype(bool)).sum()) if not preview.empty else 0,
            "d1_used_rows": int(preview["d1_used"].astype(bool).sum()) if not preview.empty else 0,
        },
        "strategy_counts": preview["strategy_id"].value_counts().to_dict() if not preview.empty else {},
    }
    write_json(summary_json, summary)

    print(json.dumps({
        "cycle_ok": True,
        "preview_rows": int(len(preview)),
        "strict_no_future_ng_rows": summary["audit"]["strict_no_future_ng_rows"],
        "h1_confirmed_ng_rows": summary["audit"]["h1_confirmed_ng_rows"],
        "h4_confirmed_ng_rows": summary["audit"]["h4_confirmed_ng_rows"],
        "d1_used": False,
        "preview_csv": str(preview_csv),
        "summary_json": str(summary_json),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

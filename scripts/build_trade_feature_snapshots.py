#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build feature snapshots for trade AI review.

This script does not call AI. It creates:
- trade_feature_snapshot.csv: compact numeric/tabular features for aggregation
- trade_feature_snapshot.jsonl: detailed pre/post candle context for AI payloads

Leak-control principle:
- pre_entry_* fields are for signal quality review
- post_entry_* fields are for outcome explanation only
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import pandas as pd

from trade_ai_review_utils import (
    FEATURE_SNAPSHOT_VERSION,
    add_indicators,
    bars_to_records,
    canonical_trade_id,
    clean_float,
    clean_str,
    normalize_direction,
    normalize_ohlcv_columns,
    parse_time_any,
    read_csv,
    record_to_jsonable,
    trend_direction,
    utc_now_text,
    write_csv,
    write_json,
    write_jsonl,
)

SNAPSHOT_COLUMNS = [
    "feature_snapshot_version",
    "created_at_utc",
    "trade_id",
    "order_key",
    "payload_key",
    "signal_key",
    "symbol",
    "broker_symbol",
    "strategy_key",
    "strategy_id",
    "direction",
    "outcome",
    "profit_r",
    "entry_time",
    "entry_price",
    "sl_price",
    "tp_price",
    "close_time",
    "close_price",
    "pre_m15_bars_requested",
    "post_m15_bars_requested",
    "pre_m15_bars_available",
    "post_m15_bars_available",
    "entry_position_in_m15_range_100_pct",
    "m15_range_100_high",
    "m15_range_100_low",
    "m15_trend_20_direction",
    "m15_trend_50_direction",
    "m15_trend_100_direction",
    "m15_atr14_at_entry",
    "m15_signal_candle_range",
    "m15_signal_candle_range_atr_ratio",
    "m15_signal_candle_body_ratio",
    "m15_signal_candle_close_pos",
    "m15_ema20_distance_atr",
    "m15_ema50_distance_atr",
    "m15_ema200_distance_atr",
    "m15_macd_hist_at_entry",
    "m15_macd_hist_delta_at_entry",
    "m15_recent_large_candle_count_20",
    "m15_recent_breakout_high_count_20",
    "m15_recent_breakout_low_count_20",
    "pre_h1_bars_available",
    "h1_trend_20_direction",
    "h1_trend_50_direction",
    "h1_close_vs_ema20_atr",
    "h1_close_vs_ema50_atr",
    "h1_close_vs_ema200_atr",
    "pre_h4_bars_available",
    "h4_trend_20_direction",
    "h4_close_vs_ema20_atr",
    "h4_close_vs_ema50_atr",
    "pre_d1_bars_available",
    "d1_trend_20_direction",
    "d1_close_vs_ema20_atr",
    "m5_first_touch_outcome",
    "m5_first_touch_time",
    "m5_mfe_points",
    "m5_mae_points",
    "m5_mfe_r",
    "m5_mae_r",
    "notes",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build trade feature snapshots for AI review payloads.")
    p.add_argument("--trade-outcome-csv", required=True)
    p.add_argument("--m15-csv", required=True)
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--d1-csv", default="")
    p.add_argument("--output-csv", required=True)
    p.add_argument("--output-jsonl", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--pre-m5-bars", type=int, default=100)
    p.add_argument("--post-m5-bars", type=int, default=240)
    p.add_argument("--pre-h1-bars", type=int, default=100)
    p.add_argument("--pre-h4-bars", type=int, default=60)
    p.add_argument("--pre-d1-bars", type=int, default=40)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return p.parse_args()


def load_tf(path: str) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    return add_indicators(read_csv(path))


def slice_pre_post(df: pd.DataFrame, entry_time: pd.Timestamp, pre: int, post: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series | None]:
    if df.empty or entry_time is None:
        return pd.DataFrame(), pd.DataFrame(), None
    work = df.copy()
    before = work[work["time"] <= entry_time].copy()
    after = work[work["time"] > entry_time].copy()
    pre_df = before.tail(pre).copy()
    post_df = after.head(post).copy()
    entry_bar = before.iloc[-1] if not before.empty else None
    return pre_df, post_df, entry_bar


def close_vs_ema_atr(row: pd.Series | None, ema_col: str) -> float | None:
    if row is None or ema_col not in row.index:
        return None
    close = clean_float(row.get("close"))
    ema = clean_float(row.get(ema_col))
    atr = clean_float(row.get("atr14"))
    if close is None or ema is None or atr is None or abs(atr) <= 1e-12:
        return None
    return (close - ema) / abs(atr)


def summarize_m15(pre_df: pd.DataFrame, post_df: pd.DataFrame, entry_bar: pd.Series | None, entry_price: float | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "pre_m15_bars_available": int(len(pre_df)),
        "post_m15_bars_available": int(len(post_df)),
    }
    if pre_df.empty or entry_bar is None:
        return out
    high_100 = clean_float(pre_df["high"].max())
    low_100 = clean_float(pre_df["low"].min())
    out["m15_range_100_high"] = high_100
    out["m15_range_100_low"] = low_100
    if entry_price is not None and high_100 is not None and low_100 is not None and high_100 > low_100:
        out["entry_position_in_m15_range_100_pct"] = (entry_price - low_100) / (high_100 - low_100) * 100.0
    out["m15_trend_20_direction"] = trend_direction(pre_df["close"].tail(20))
    out["m15_trend_50_direction"] = trend_direction(pre_df["close"].tail(50))
    out["m15_trend_100_direction"] = trend_direction(pre_df["close"].tail(100))
    atr = clean_float(entry_bar.get("atr14"))
    candle_range = clean_float(entry_bar.get("high"))
    low = clean_float(entry_bar.get("low"))
    if candle_range is not None and low is not None:
        candle_range = candle_range - low
    out["m15_atr14_at_entry"] = atr
    out["m15_signal_candle_range"] = candle_range
    out["m15_signal_candle_range_atr_ratio"] = None if atr is None or candle_range is None or abs(atr) <= 1e-12 else candle_range / abs(atr)
    out["m15_signal_candle_body_ratio"] = clean_float(entry_bar.get("body_ratio"))
    out["m15_signal_candle_close_pos"] = clean_float(entry_bar.get("close_pos"))
    close = clean_float(entry_bar.get("close"))
    for ema in ["ema20", "ema50", "ema200"]:
        value = None
        ema_value = clean_float(entry_bar.get(ema))
        if close is not None and ema_value is not None and atr is not None and abs(atr) > 1e-12:
            value = (close - ema_value) / abs(atr)
        out[f"m15_{ema}_distance_atr"] = value
    out["m15_macd_hist_at_entry"] = clean_float(entry_bar.get("macd_hist"))
    out["m15_macd_hist_delta_at_entry"] = clean_float(entry_bar.get("macd_hist_delta"))
    if atr is not None and abs(atr) > 1e-12 and "high" in pre_df.columns and "low" in pre_df.columns:
        recent = pre_df.tail(20).copy()
        ranges = (recent["high"] - recent["low"]).abs()
        out["m15_recent_large_candle_count_20"] = int((ranges / abs(atr) >= 1.5).sum())
        out["m15_recent_breakout_high_count_20"] = int((recent["high"] >= recent["high"].rolling(8, min_periods=1).max().shift(1)).fillna(False).sum())
        out["m15_recent_breakout_low_count_20"] = int((recent["low"] <= recent["low"].rolling(8, min_periods=1).min().shift(1)).fillna(False).sum())
    return out


def summarize_higher(prefix: str, pre_df: pd.DataFrame, entry_bar: pd.Series | None) -> dict[str, Any]:
    out: dict[str, Any] = {f"pre_{prefix}_bars_available": int(len(pre_df))}
    if pre_df.empty or entry_bar is None:
        return out
    out[f"{prefix}_trend_20_direction"] = trend_direction(pre_df["close"].tail(20))
    if prefix == "h1":
        out[f"{prefix}_trend_50_direction"] = trend_direction(pre_df["close"].tail(50))
    out[f"{prefix}_close_vs_ema20_atr"] = close_vs_ema_atr(entry_bar, "ema20")
    out[f"{prefix}_close_vs_ema50_atr"] = close_vs_ema_atr(entry_bar, "ema50")
    if prefix == "h1":
        out[f"{prefix}_close_vs_ema200_atr"] = close_vs_ema_atr(entry_bar, "ema200")
    return out


def evaluate_m5_path(m5_df: pd.DataFrame, trade: pd.Series, args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {
        "m5_first_touch_outcome": "NO_M5_PATH",
        "m5_first_touch_time": "",
        "m5_mfe_points": None,
        "m5_mae_points": None,
        "m5_mfe_r": None,
        "m5_mae_r": None,
    }
    if m5_df.empty:
        return out
    entry_time = parse_time_any(trade.get("entry_time"))
    if entry_time is None:
        return out
    direction = normalize_direction(trade.get("direction"))
    entry = clean_float(trade.get("entry_price"), clean_float(trade.get("entry_price_reference")))
    sl = clean_float(trade.get("sl_price"))
    tp = clean_float(trade.get("tp_price"))
    if entry is None or sl is None or tp is None or direction not in {"BUY", "SELL"}:
        return out
    path = m5_df[m5_df["time"] > entry_time].head(int(args.post_m5_bars)).copy()
    if path.empty:
        return out
    stop_dist = abs(entry - sl)
    if stop_dist <= 1e-12:
        stop_dist = None
    if direction == "BUY":
        favorable = path["high"] - entry
        adverse = path["low"] - entry
        tp_hit = path["high"] >= tp
        sl_hit = path["low"] <= sl
    else:
        favorable = entry - path["low"]
        adverse = entry - path["high"]
        tp_hit = path["low"] <= tp
        sl_hit = path["high"] >= sl
    out["m5_mfe_points"] = clean_float(favorable.max())
    out["m5_mae_points"] = clean_float(adverse.min())
    if stop_dist:
        out["m5_mfe_r"] = out["m5_mfe_points"] / stop_dist if out["m5_mfe_points"] is not None else None
        out["m5_mae_r"] = out["m5_mae_points"] / stop_dist if out["m5_mae_points"] is not None else None
    for _, row in path.iterrows():
        is_tp = bool(tp_hit.loc[row.name])
        is_sl = bool(sl_hit.loc[row.name])
        if is_tp and is_sl:
            out["m5_first_touch_outcome"] = args.inbar_priority
            out["m5_first_touch_time"] = row["time"].strftime("%Y-%m-%d %H:%M:%S")
            return out
        if is_tp:
            out["m5_first_touch_outcome"] = "TP"
            out["m5_first_touch_time"] = row["time"].strftime("%Y-%m-%d %H:%M:%S")
            return out
        if is_sl:
            out["m5_first_touch_outcome"] = "SL"
            out["m5_first_touch_time"] = row["time"].strftime("%Y-%m-%d %H:%M:%S")
            return out
    out["m5_first_touch_outcome"] = "UNRESOLVED_WITHIN_M5_WINDOW"
    return out


def build_one_snapshot(trade: pd.Series, dfs: dict[str, pd.DataFrame], args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    entry_time = parse_time_any(trade.get("entry_time"))
    entry_price = clean_float(trade.get("entry_price"), clean_float(trade.get("entry_price_reference")))
    base = {
        "feature_snapshot_version": FEATURE_SNAPSHOT_VERSION,
        "created_at_utc": utc_now_text(),
        "trade_id": clean_str(trade.get("trade_id"), canonical_trade_id(trade)),
        "order_key": clean_str(trade.get("order_key")),
        "payload_key": clean_str(trade.get("payload_key")),
        "signal_key": clean_str(trade.get("signal_key")),
        "symbol": clean_str(trade.get("symbol")),
        "broker_symbol": clean_str(trade.get("broker_symbol")),
        "strategy_key": clean_str(trade.get("strategy_key")),
        "strategy_id": clean_str(trade.get("strategy_id")),
        "direction": normalize_direction(trade.get("direction")),
        "outcome": clean_str(trade.get("outcome")),
        "profit_r": clean_float(trade.get("profit_r")),
        "entry_time": clean_str(trade.get("entry_time")),
        "entry_price": entry_price,
        "sl_price": clean_float(trade.get("sl_price")),
        "tp_price": clean_float(trade.get("tp_price")),
        "close_time": clean_str(trade.get("close_time")),
        "close_price": clean_float(trade.get("close_price")),
        "pre_m15_bars_requested": int(args.pre_m15_bars),
        "post_m15_bars_requested": int(args.post_m15_bars),
        "notes": "pre-entry data for signal quality; post-entry data for outcome explanation only",
    }
    pre_m15, post_m15, entry_m15 = slice_pre_post(dfs["m15"], entry_time, args.pre_m15_bars, args.post_m15_bars) if entry_time is not None else (pd.DataFrame(), pd.DataFrame(), None)
    base.update(summarize_m15(pre_m15, post_m15, entry_m15, entry_price))
    for tf, pre_n in [("h1", args.pre_h1_bars), ("h4", args.pre_h4_bars), ("d1", args.pre_d1_bars)]:
        if dfs[tf].empty or entry_time is None:
            base.update(summarize_higher(tf, pd.DataFrame(), None))
            continue
        pre_df, _, entry_bar = slice_pre_post(dfs[tf], entry_time, pre_n, 0)
        base.update(summarize_higher(tf, pre_df, entry_bar))
    base.update(evaluate_m5_path(dfs["m5"], trade, args))
    compact = {col: base.get(col, "") for col in SNAPSHOT_COLUMNS}
    detail = {
        "feature_snapshot_version": FEATURE_SNAPSHOT_VERSION,
        "created_at_utc": base["created_at_utc"],
        "trade": {k: (None if pd.isna(v) else v) for k, v in trade.to_dict().items()},
        "compact_features": compact,
        "leak_control": {
            "pre_entry_data_use": "signal_quality_review_only",
            "post_entry_data_use": "outcome_explanation_only",
            "rule": "Do not use post-entry movement to invent pre-entry reasons.",
        },
        "m15": {
            "pre_entry_bars_requested": int(args.pre_m15_bars),
            "post_entry_bars_requested": int(args.post_m15_bars),
            "pre_entry_bars": bars_to_records(pre_m15),
            "post_entry_bars": bars_to_records(post_m15),
        },
    }
    for tf, pre_n in [("h1", args.pre_h1_bars), ("h4", args.pre_h4_bars), ("d1", args.pre_d1_bars)]:
        pre_df = pd.DataFrame()
        if not dfs[tf].empty and entry_time is not None:
            pre_df, _, _ = slice_pre_post(dfs[tf], entry_time, pre_n, 0)
        detail[tf] = {
            "pre_entry_bars_requested": int(pre_n),
            "pre_entry_bars": bars_to_records(pre_df),
        }
    return compact, detail


def main() -> int:
    args = parse_args()
    trades = read_csv(args.trade_outcome_csv)
    dfs = {
        "m15": load_tf(args.m15_csv),
        "m5": load_tf(args.m5_csv),
        "h1": load_tf(args.h1_csv),
        "h4": load_tf(args.h4_csv),
        "d1": load_tf(args.d1_csv),
    }
    compact_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    for _, trade in trades.iterrows():
        compact, detail = build_one_snapshot(trade, dfs, args)
        compact_rows.append(compact)
        detail_rows.append(detail)
    out_df = pd.DataFrame(compact_rows, columns=SNAPSHOT_COLUMNS)
    write_csv(out_df, args.output_csv)
    jsonl_count = write_jsonl(args.output_jsonl, detail_rows)
    summary = {
        "script": "build_trade_feature_snapshots.py",
        "created_at_utc": utc_now_text(),
        "trade_outcome_csv": args.trade_outcome_csv,
        "m15_csv": args.m15_csv,
        "m5_csv": args.m5_csv,
        "h1_csv": args.h1_csv,
        "h4_csv": args.h4_csv,
        "d1_csv": args.d1_csv,
        "output_csv": args.output_csv,
        "output_jsonl": args.output_jsonl,
        "rows_in": int(len(trades)),
        "rows_out_csv": int(len(out_df)),
        "rows_out_jsonl": int(jsonl_count),
        "tf_rows": {tf: int(len(df)) for tf, df in dfs.items()},
    }
    if args.output_json:
        write_json(args.output_json, summary)
    print("build_trade_feature_snapshots")
    print(f"rows_in: {summary['rows_in']}")
    print(f"rows_out_csv: {summary['rows_out_csv']}")
    print(f"rows_out_jsonl: {summary['rows_out_jsonl']}")
    print(f"output_csv: {args.output_csv}")
    print(f"output_jsonl: {args.output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

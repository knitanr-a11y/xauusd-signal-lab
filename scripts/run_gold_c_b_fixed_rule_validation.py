#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate fixed GOLD C+B divergence reversal rule.

This script is intentionally a validation script, not a live notifier.

Rule under test
---------------
Name:
    GOLD_H4_PERMISSION_H1_REGULAR_BULLISH_M15_BREAK

Direction:
    BUY only

H4 permission:
    At the M15 signal close time, BUY is allowed when either:
      1. latest confirmed H4 candle is in up environment:
           h4_ema20 > h4_ema50 and h4_close > h4_ema50
      2. latest confirmed H4 regular bullish divergence was confirmed within
         the configured permission window, e.g. 48h or 72h.

H1 context:
    A newly confirmed H1 LOW pivot has regular bullish divergence and is in a
    loose sell-exhaustion state:
        h1_latest_low_div_type == "regular_bullish"
        and (h1_close < h1_ema50 or h1_ema20 < h1_ema50)

M15 trigger:
    After the H1 event confirmation, take the first M15 BUY trigger:
        close > previous rolling high over N bars
        close > ema20
        macd(6,13,4) > signal
        macd_hist > previous macd_hist

Entry / exit:
    Entry = M15 close at signal close time.
    SL    = M15 rolling low over the latest 12 bars - ATR14 * 0.05.
    TP    = RR * risk. Default RR=1.5.
    Outcome is judged by M5 first-touch for a fixed horizon.
    If TP and SL touch in the same M5 candle, SL wins by default.

Safety / no-lookahead
---------------------
- CSV `time` is candle open time.
- Every row becomes usable only at `close_time = time + timeframe`.
- H4 permission is matched to M15 by confirmed close time only.
- H1 divergence is used only at the pivot confirmation close time.
- M15 entry is searched only after H1 confirmation.
- Outcome uses M5 candles at/after the M15 entry time.

Outputs
-------
In --out-dir:
    fixed_rule_summary.csv
    fixed_rule_monthly.csv
    fixed_rule_trades_48h.csv
    fixed_rule_trades_72h.csv
    extra_trades_added_by_72h.csv
    fixed_rule_equity_curve.csv
    context_events_h1_regular_bullish_loose.csv
    h4_regular_bullish_events.csv
    m15_trigger_candidates.csv
    README_conditions.txt

Example
-------
python scripts/run_gold_c_b_fixed_rule_validation.py ^
  --csv-dir "C:\\Users\\regen\\AppData\\Roaming\\MetaQuotes\\Terminal\\2FA8A7E69CED7DC259B1AD86A247F675\\MQL5\\Files" ^
  --out-dir data\\results\\gold_c_b_fixed_rule_validation
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.mochipoyo_minimal_config import resolve_csv_path
    from scripts.scan_mochipoyo_multi_tf_candidates import add_indicators, ema, read_ohlc_csv
except ModuleNotFoundError:  # direct execution from scripts/
    from mochipoyo_minimal_config import resolve_csv_path  # type: ignore
    from scan_mochipoyo_multi_tf_candidates import add_indicators, ema, read_ohlc_csv  # type: ignore


def parse_windows_hours(text: str) -> list[int]:
    values: list[int] = []
    for raw in str(text).split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = int(raw)
        if value <= 0:
            raise ValueError(f"permission window must be positive hours: {value}")
        values.append(value)
    if not values:
        raise ValueError("--permission-windows-hours must contain at least one value")
    return values


def parse_timestamp_or_none(value: str | None) -> pd.Timestamp | None:
    if value is None or str(value).strip() == "":
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid datetime: {value!r}")
    return pd.Timestamp(ts)


def safe_float(value: object, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def ensure_datetime_columns(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def add_fixed_rule_indicators(df: pd.DataFrame, tf: str, args: argparse.Namespace) -> pd.DataFrame:
    """Reuse the existing audited indicator stack, then add EMA50 and helper columns."""
    out = add_indicators(
        df,
        tf,
        zigzag_depth=args.zigzag_depth,
        zigzag_deviation=args.zigzag_deviation,
        zigzag_deviation_mode=args.zigzag_deviation_mode,
        point_size=args.point_size,
        zigzag_backstep=args.zigzag_backstep,
    )
    out["ema50"] = ema(out["close"], 50)
    out["macd_hist_delta"] = out["macd_hist"] - out["macd_hist"].shift(1)
    out["tf"] = tf
    return ensure_datetime_columns(
        out,
        [
            "time",
            "close_time",
            "latest_low_pivot_time",
            "latest_low_confirm_time",
            "latest_high_pivot_time",
            "latest_high_confirm_time",
        ],
    )


def load_gold_csvs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    overrides = {
        "gold_h4": args.gold_h4_csv,
        "gold_h1": args.gold_h1_csv,
        "gold_m15": args.gold_m15_csv,
        "gold_m5": args.gold_m5_csv,
    }
    h4 = read_ohlc_csv(resolve_csv_path(args.csv_dir, "gold_h4", overrides))
    h1 = read_ohlc_csv(resolve_csv_path(args.csv_dir, "gold_h1", overrides))
    m15 = read_ohlc_csv(resolve_csv_path(args.csv_dir, "gold_m15", overrides))
    m5 = read_ohlc_csv(resolve_csv_path(args.csv_dir, "gold_m5", overrides))
    return h4, h1, m15, m5


def apply_time_filter(df: pd.DataFrame, *, start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    out = df.copy()
    if start is not None:
        out = out[out["time"] >= start]
    if end is not None:
        out = out[out["time"] <= end]
    return out.reset_index(drop=True)


def build_h4_permission_frame(h4: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return all confirmed H4 rows and newly confirmed H4 regular bullish div events."""
    h4 = ensure_datetime_columns(h4, ["time", "close_time", "latest_low_pivot_time", "latest_low_confirm_time"]).copy()
    h4["h4_env_up"] = (h4["ema20"] > h4["ema50"]) & (h4["close"] > h4["ema50"])
    h4["h4_regular_bullish_new"] = (
        h4["latest_low_confirm_time"].notna()
        & (h4["latest_low_confirm_time"] == h4["close_time"])
        & (h4["latest_low_div_type"].astype(str) == "regular_bullish")
    )

    events = h4[h4["h4_regular_bullish_new"]].copy()
    if events.empty:
        event_cols = [
            "h4_event_id",
            "h4_event_confirm_time",
            "h4_pivot_time",
            "h4_pivot_price",
            "h4_close",
            "h4_ema20",
            "h4_ema50",
            "h4_macd",
            "h4_macd_signal",
            "h4_macd_hist",
        ]
        return h4, pd.DataFrame(columns=event_cols)

    events = events.drop_duplicates(
        subset=["latest_low_pivot_time", "latest_low_confirm_time", "latest_low_price", "latest_low_div_type"],
        keep="first",
    ).reset_index(drop=True)
    events["h4_event_confirm_time"] = events["close_time"]
    events["h4_pivot_time"] = events["latest_low_pivot_time"]
    events["h4_pivot_price"] = events["latest_low_price"]
    events["h4_event_id"] = [
        f"H4_REG_BULL_{pd.Timestamp(row.h4_event_confirm_time).strftime('%Y%m%d%H%M')}_{i:04d}"
        for i, row in events.reset_index(drop=True).iterrows()
    ]

    keep = [
        "h4_event_id",
        "h4_event_confirm_time",
        "h4_pivot_time",
        "h4_pivot_price",
        "close",
        "ema20",
        "ema50",
        "macd",
        "macd_signal",
        "macd_hist",
    ]
    events = events[keep].rename(
        columns={
            "close": "h4_close",
            "ema20": "h4_ema20",
            "ema50": "h4_ema50",
            "macd": "h4_macd",
            "macd_signal": "h4_macd_signal",
            "macd_hist": "h4_macd_hist",
        }
    )
    return h4, events


def build_h1_context_events(h1: pd.DataFrame) -> pd.DataFrame:
    """Find H1 regular bullish loose sell-exhaustion events."""
    h1 = ensure_datetime_columns(h1, ["time", "close_time", "latest_low_pivot_time", "latest_low_confirm_time"]).copy()
    is_new_regular_bullish = (
        h1["latest_low_confirm_time"].notna()
        & (h1["latest_low_confirm_time"] == h1["close_time"])
        & (h1["latest_low_div_type"].astype(str) == "regular_bullish")
    )
    loose_sell_exhaustion = (h1["close"] < h1["ema50"]) | (h1["ema20"] < h1["ema50"])
    events = h1[is_new_regular_bullish & loose_sell_exhaustion].copy()
    if events.empty:
        return pd.DataFrame(
            columns=[
                "h1_event_id",
                "h1_event_confirm_time",
                "h1_pivot_time",
                "h1_pivot_price",
                "h1_close",
                "h1_ema20",
                "h1_ema50",
                "h1_macd",
                "h1_macd_signal",
                "h1_macd_hist",
            ]
        )

    events = events.drop_duplicates(
        subset=["latest_low_pivot_time", "latest_low_confirm_time", "latest_low_price", "latest_low_div_type"],
        keep="first",
    ).reset_index(drop=True)
    events["h1_event_confirm_time"] = events["close_time"]
    events["h1_pivot_time"] = events["latest_low_pivot_time"]
    events["h1_pivot_price"] = events["latest_low_price"]
    events["h1_event_id"] = [
        f"H1_REG_BULL_{pd.Timestamp(row.h1_event_confirm_time).strftime('%Y%m%d%H%M')}_{i:04d}"
        for i, row in events.reset_index(drop=True).iterrows()
    ]

    keep = [
        "h1_event_id",
        "h1_event_confirm_time",
        "h1_pivot_time",
        "h1_pivot_price",
        "close",
        "ema20",
        "ema50",
        "macd",
        "macd_signal",
        "macd_hist",
    ]
    return events[keep].rename(
        columns={
            "close": "h1_close",
            "ema20": "h1_ema20",
            "ema50": "h1_ema50",
            "macd": "h1_macd",
            "macd_signal": "h1_macd_signal",
            "macd_hist": "h1_macd_hist",
        }
    )


def build_m15_trigger_candidates(m15: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = m15.copy()
    out["m15_breakout_high_prev"] = out["high"].shift(1).rolling(args.m15_breakout_lookback, min_periods=args.m15_breakout_lookback).max()
    out["m15_sl_base_low"] = out["low"].rolling(args.sl_lookback_m15, min_periods=args.sl_lookback_m15).min()
    out["m15_buy_trigger"] = (
        (out["close"] > out["m15_breakout_high_prev"])
        & (out["close"] > out["ema20"])
        & (out["macd"] > out["macd_signal"])
        & (out["macd_hist"] > out["macd_hist"].shift(1))
        & out["m15_sl_base_low"].notna()
        & out["atr14"].notna()
    )
    out = out[out["m15_buy_trigger"]].copy()
    if out.empty:
        return pd.DataFrame(
            columns=[
                "m15_time",
                "m15_close_time",
                "entry_time",
                "entry_price",
                "m15_breakout_high_prev",
                "m15_sl_base_low",
                "m15_atr14",
                "m15_ema20",
                "m15_macd",
                "m15_macd_signal",
                "m15_macd_hist",
            ]
        )
    out["m15_time"] = out["time"]
    out["m15_close_time"] = out["close_time"]
    out["entry_time"] = out["close_time"]
    out["entry_price"] = out["close"]
    keep = [
        "m15_time",
        "m15_close_time",
        "entry_time",
        "entry_price",
        "m15_breakout_high_prev",
        "m15_sl_base_low",
        "atr14",
        "ema20",
        "macd",
        "macd_signal",
        "macd_hist",
        "open",
        "high",
        "low",
        "close",
    ]
    return out[keep].rename(
        columns={
            "atr14": "m15_atr14",
            "ema20": "m15_ema20",
            "macd": "m15_macd",
            "macd_signal": "m15_macd_signal",
            "macd_hist": "m15_macd_hist",
            "open": "m15_open",
            "high": "m15_high",
            "low": "m15_low",
            "close": "m15_close",
        }
    ).reset_index(drop=True)


def add_h4_permission_to_triggers(
    m15_triggers: pd.DataFrame,
    h4_all: pd.DataFrame,
    h4_events: pd.DataFrame,
    windows_hours: list[int],
) -> pd.DataFrame:
    """Attach latest confirmed H4 environment and latest H4 regular div event to each M15 trigger."""
    if m15_triggers.empty:
        return m15_triggers.copy()

    triggers = m15_triggers.copy().sort_values("m15_close_time").reset_index(drop=True)

    h4_env = h4_all[
        [
            "close_time",
            "time",
            "close",
            "ema20",
            "ema50",
            "macd",
            "macd_signal",
            "macd_hist",
            "h4_env_up",
        ]
    ].copy().sort_values("close_time")
    h4_env = h4_env.rename(
        columns={
            "close_time": "h4_close_time",
            "time": "h4_time",
            "close": "h4_close",
            "ema20": "h4_ema20",
            "ema50": "h4_ema50",
            "macd": "h4_macd",
            "macd_signal": "h4_macd_signal",
            "macd_hist": "h4_macd_hist",
        }
    )

    out = pd.merge_asof(
        triggers.sort_values("m15_close_time"),
        h4_env.sort_values("h4_close_time"),
        left_on="m15_close_time",
        right_on="h4_close_time",
        direction="backward",
    ).reset_index(drop=True)

    if h4_events.empty:
        out["h4_event_id"] = ""
        out["h4_event_confirm_time"] = pd.NaT
        out["h4_pivot_time"] = pd.NaT
        out["h4_pivot_price"] = np.nan
    else:
        h4_ev = h4_events.copy().sort_values("h4_event_confirm_time")
        out = pd.merge_asof(
            out.sort_values("m15_close_time"),
            h4_ev,
            left_on="m15_close_time",
            right_on="h4_event_confirm_time",
            direction="backward",
            suffixes=("", "_event"),
        ).reset_index(drop=True)

    for hours in windows_hours:
        col = f"h4_permission_{hours}h"
        age_col = f"h4_regular_bullish_age_hours_{hours}h"
        age_hours = (out["m15_close_time"] - out["h4_event_confirm_time"]).dt.total_seconds() / 3600.0
        out[age_col] = age_hours
        recent_regular = out["h4_event_confirm_time"].notna() & (age_hours >= 0) & (age_hours <= float(hours))
        out[col] = out["h4_env_up"].fillna(False) | recent_regular
    return out.sort_values("m15_close_time", kind="mergesort").reset_index(drop=True)


def first_trigger_for_h1_event(
    h1_event: pd.Series,
    m15_with_permission: pd.DataFrame,
    *,
    window_hours: int,
    entry_search_hours: float,
) -> pd.Series | None:
    start = pd.Timestamp(h1_event["h1_event_confirm_time"])
    end = start + pd.to_timedelta(entry_search_hours, unit="h")
    perm_col = f"h4_permission_{window_hours}h"
    cands = m15_with_permission[
        (m15_with_permission["m15_close_time"] >= start)
        & (m15_with_permission["m15_close_time"] <= end)
        & (m15_with_permission[perm_col].fillna(False))
    ].copy()
    if cands.empty:
        return None
    return cands.sort_values("m15_close_time", kind="mergesort").iloc[0]


def judge_buy_first_touch(
    m5: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    horizon_hours: float,
    inbar_priority: str,
) -> dict[str, object]:
    risk = entry_price - sl_price
    if not math.isfinite(risk) or risk <= 0:
        return {
            "outcome": "INVALID_RISK",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
        }

    end_time = entry_time + pd.to_timedelta(horizon_hours, unit="h")
    path = m5[(m5["time"] >= entry_time) & (m5["time"] < end_time)].copy()
    if path.empty:
        return {
            "outcome": "NO_M5_PATH",
            "exit_time": pd.NaT,
            "exit_price": np.nan,
            "realized_r": np.nan,
            "bars_checked": 0,
        }

    for _, bar in path.iterrows():
        hit_sl = safe_float(bar["low"]) <= sl_price
        hit_tp = safe_float(bar["high"]) >= tp_price
        if hit_sl and hit_tp:
            if str(inbar_priority).upper() == "TP":
                return {
                    "outcome": "WIN",
                    "exit_time": bar["time"],
                    "exit_price": tp_price,
                    "realized_r": (tp_price - entry_price) / risk,
                    "bars_checked": int(len(path[path["time"] <= bar["time"]])),
                }
            return {
                "outcome": "LOSS",
                "exit_time": bar["time"],
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": int(len(path[path["time"] <= bar["time"]])),
            }
        if hit_sl:
            return {
                "outcome": "LOSS",
                "exit_time": bar["time"],
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": int(len(path[path["time"] <= bar["time"]])),
            }
        if hit_tp:
            return {
                "outcome": "WIN",
                "exit_time": bar["time"],
                "exit_price": tp_price,
                "realized_r": (tp_price - entry_price) / risk,
                "bars_checked": int(len(path[path["time"] <= bar["time"]])),
            }

    last = path.iloc[-1]
    exit_price = safe_float(last["close"])
    return {
        "outcome": "TIMEOUT",
        "exit_time": last["time"],
        "exit_price": exit_price,
        "realized_r": (exit_price - entry_price) / risk,
        "bars_checked": int(len(path)),
    }


def build_trades_for_window(
    h1_events: pd.DataFrame,
    m15_with_permission: pd.DataFrame,
    m5: pd.DataFrame,
    *,
    window_hours: int,
    args: argparse.Namespace,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, h1_event in h1_events.sort_values("h1_event_confirm_time", kind="mergesort").iterrows():
        trigger = first_trigger_for_h1_event(
            h1_event,
            m15_with_permission,
            window_hours=window_hours,
            entry_search_hours=args.entry_search_hours,
        )
        if trigger is None:
            continue

        entry_time = pd.Timestamp(trigger["entry_time"])
        entry_price = safe_float(trigger["entry_price"])
        sl_price = safe_float(trigger["m15_sl_base_low"]) - safe_float(trigger["m15_atr14"]) * args.sl_atr_buffer_mult
        risk = entry_price - sl_price
        if not math.isfinite(risk) or risk <= 0:
            continue
        tp_price = entry_price + risk * args.rr

        outcome = judge_buy_first_touch(
            m5,
            entry_time=entry_time,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            horizon_hours=args.horizon_hours,
            inbar_priority=args.inbar_priority,
        )

        h4_recent_age = safe_float(trigger.get(f"h4_regular_bullish_age_hours_{window_hours}h"))
        h4_recent_regular = math.isfinite(h4_recent_age) and 0 <= h4_recent_age <= window_hours
        h4_env_up = bool(trigger.get("h4_env_up", False))
        if h4_env_up and h4_recent_regular:
            permission_reason = "h4_env_up_and_recent_regular_bullish"
        elif h4_env_up:
            permission_reason = "h4_env_up"
        elif h4_recent_regular:
            permission_reason = "recent_h4_regular_bullish"
        else:
            permission_reason = "UNKNOWN_SHOULD_NOT_HAPPEN"

        row = {
            "setup_name": "GOLD_H4_PERMISSION_H1_REGULAR_BULLISH_M15_BREAK",
            "symbol": "GOLD",
            "direction": "BUY",
            "permission_window_hours": window_hours,
            "h1_event_id": h1_event["h1_event_id"],
            "h1_event_confirm_time": h1_event["h1_event_confirm_time"],
            "h1_pivot_time": h1_event["h1_pivot_time"],
            "h1_pivot_price": h1_event["h1_pivot_price"],
            "h1_close": h1_event["h1_close"],
            "h1_ema20": h1_event["h1_ema20"],
            "h1_ema50": h1_event["h1_ema50"],
            "h1_macd": h1_event["h1_macd"],
            "h1_macd_signal": h1_event["h1_macd_signal"],
            "h1_macd_hist": h1_event["h1_macd_hist"],
            "h4_permission_reason": permission_reason,
            "h4_time": trigger.get("h4_time"),
            "h4_close_time": trigger.get("h4_close_time"),
            "h4_env_up": h4_env_up,
            "h4_event_id": trigger.get("h4_event_id", ""),
            "h4_event_confirm_time": trigger.get("h4_event_confirm_time"),
            "h4_pivot_time": trigger.get("h4_pivot_time"),
            "h4_pivot_price": trigger.get("h4_pivot_price"),
            "h4_regular_bullish_age_hours": h4_recent_age,
            "h4_close": trigger.get("h4_close"),
            "h4_ema20": trigger.get("h4_ema20"),
            "h4_ema50": trigger.get("h4_ema50"),
            "m15_time": trigger["m15_time"],
            "m15_close_time": trigger["m15_close_time"],
            "entry_time": entry_time,
            "entry_price": entry_price,
            "m15_breakout_high_prev": trigger["m15_breakout_high_prev"],
            "m15_sl_base_low": trigger["m15_sl_base_low"],
            "m15_atr14": trigger["m15_atr14"],
            "m15_ema20": trigger["m15_ema20"],
            "m15_macd": trigger["m15_macd"],
            "m15_macd_signal": trigger["m15_macd_signal"],
            "m15_macd_hist": trigger["m15_macd_hist"],
            "sl_price": sl_price,
            "tp_price": tp_price,
            "risk_price": risk,
            "rr": args.rr,
            **outcome,
        }
        row["trade_key"] = (
            str(row["setup_name"])
            + "|"
            + str(row["permission_window_hours"])
            + "|"
            + str(row["h1_event_id"])
            + "|"
            + pd.Timestamp(row["entry_time"]).strftime("%Y-%m-%d %H:%M:%S")
        )
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.sort_values(["entry_time", "h1_event_id"], kind="mergesort").reset_index(drop=True)
    out["entry_month"] = pd.to_datetime(out["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    out["is_win"] = out["outcome"].eq("WIN")
    out["is_loss"] = out["outcome"].eq("LOSS")
    return out


def max_drawdown_r(r_values: pd.Series) -> float:
    if r_values.empty:
        return 0.0
    equity = r_values.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    return float(dd.max()) if not dd.empty else 0.0


def summarize_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for window, g in trades.groupby("permission_window_hours", dropna=False):
        g = g.sort_values("entry_time", kind="mergesort").copy()
        r = pd.to_numeric(g["realized_r"], errors="coerce").dropna()
        gross_profit = float(r[r > 0].sum())
        gross_loss = float(-r[r < 0].sum())
        rows.append(
            {
                "permission_window_hours": int(window),
                "trades": int(len(g)),
                "wins": int(g["outcome"].eq("WIN").sum()),
                "losses": int(g["outcome"].eq("LOSS").sum()),
                "timeouts": int(g["outcome"].eq("TIMEOUT").sum()),
                "win_rate": float(g["outcome"].eq("WIN").mean()) if len(g) else np.nan,
                "total_r": float(r.sum()) if not r.empty else np.nan,
                "avg_r": float(r.mean()) if not r.empty else np.nan,
                "gross_profit_r": gross_profit,
                "gross_loss_r": gross_loss,
                "profit_factor": float("inf") if gross_loss == 0 and gross_profit > 0 else (gross_profit / gross_loss if gross_loss > 0 else np.nan),
                "max_dd_r": max_drawdown_r(r),
                "first_entry_time": str(g["entry_time"].min()),
                "last_entry_time": str(g["entry_time"].max()),
                "months_with_trades": int(g["entry_month"].nunique()),
            }
        )
    return pd.DataFrame(rows).sort_values("permission_window_hours").reset_index(drop=True)


def summarize_monthly(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for (window, month), g in trades.groupby(["permission_window_hours", "entry_month"], dropna=False):
        r = pd.to_numeric(g["realized_r"], errors="coerce").dropna()
        gross_profit = float(r[r > 0].sum())
        gross_loss = float(-r[r < 0].sum())
        rows.append(
            {
                "permission_window_hours": int(window),
                "entry_month": str(month),
                "trades": int(len(g)),
                "wins": int(g["outcome"].eq("WIN").sum()),
                "losses": int(g["outcome"].eq("LOSS").sum()),
                "timeouts": int(g["outcome"].eq("TIMEOUT").sum()),
                "win_rate": float(g["outcome"].eq("WIN").mean()) if len(g) else np.nan,
                "total_r": float(r.sum()) if not r.empty else np.nan,
                "avg_r": float(r.mean()) if not r.empty else np.nan,
                "profit_factor": float("inf") if gross_loss == 0 and gross_profit > 0 else (gross_profit / gross_loss if gross_loss > 0 else np.nan),
                "max_dd_r": max_drawdown_r(r),
            }
        )
    return pd.DataFrame(rows).sort_values(["permission_window_hours", "entry_month"]).reset_index(drop=True)


def build_equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    out = trades.sort_values(["permission_window_hours", "entry_time"], kind="mergesort").copy()
    out["realized_r"] = pd.to_numeric(out["realized_r"], errors="coerce")
    out["cum_r"] = out.groupby("permission_window_hours")["realized_r"].cumsum()
    out["peak_r"] = out.groupby("permission_window_hours")["cum_r"].cummax()
    out["drawdown_r"] = out["peak_r"] - out["cum_r"]
    return out[
        [
            "permission_window_hours",
            "entry_time",
            "entry_month",
            "trade_key",
            "outcome",
            "realized_r",
            "cum_r",
            "peak_r",
            "drawdown_r",
        ]
    ].reset_index(drop=True)


def write_readme(args: argparse.Namespace, out_dir: Path, windows_hours: list[int]) -> None:
    text = f"""# GOLD C+B fixed rule validation

Generated by:
`scripts/run_gold_c_b_fixed_rule_validation.py`

## Fixed rule

BUY only.

H4 permission:
- latest confirmed H4 environment is up: `ema20 > ema50 and close > ema50`
- OR latest confirmed H4 regular bullish divergence is within one of:
  `{','.join(map(str, windows_hours))}` hours.

H1 context:
- newly confirmed H1 LOW pivot regular bullish divergence
- loose sell-exhaustion:
  `close < ema50 or ema20 < ema50`

M15 entry:
- `close > high.shift(1).rolling({args.m15_breakout_lookback}).max()`
- `close > ema20`
- `macd(6,13,4) > signal`
- `macd_hist > macd_hist.shift(1)`
- first M15 trigger within `{args.entry_search_hours}` hours after the H1 event confirmation

SL/TP:
- Entry = M15 close
- SL = M15 rolling low {args.sl_lookback_m15} bars - ATR14 * {args.sl_atr_buffer_mult}
- TP = RR {args.rr}
- Outcome = M5 first-touch, horizon {args.horizon_hours} hours
- In-bar priority = {args.inbar_priority}

Pivot/divergence:
- Uses existing `scripts.scan_mochipoyo_multi_tf_candidates.add_indicators`.
- zigzag_depth={args.zigzag_depth}
- zigzag_deviation={args.zigzag_deviation}
- zigzag_deviation_mode={args.zigzag_deviation_mode}
- zigzag_backstep={args.zigzag_backstep}
- point_size={args.point_size}

## Outputs

- `fixed_rule_summary.csv`
- `fixed_rule_monthly.csv`
- `fixed_rule_trades_48h.csv`
- `fixed_rule_trades_72h.csv`
- `extra_trades_added_by_72h.csv`
- `fixed_rule_equity_curve.csv`
- `context_events_h1_regular_bullish_loose.csv`
- `h4_regular_bullish_events.csv`
- `m15_trigger_candidates.csv`
"""
    (out_dir / "README_conditions.txt").write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate GOLD H4 permission + H1 regular bullish + M15 break fixed rule.")
    p.add_argument("--csv-dir", type=Path, required=True, help="Directory containing goldsharp_h4/h1/m15/m5 CSVs.")
    p.add_argument("--out-dir", type=Path, default=Path("data/results/gold_c_b_fixed_rule_validation"))
    p.add_argument("--gold-h4-csv", type=Path, default=None)
    p.add_argument("--gold-h1-csv", type=Path, default=None)
    p.add_argument("--gold-m15-csv", type=Path, default=None)
    p.add_argument("--gold-m5-csv", type=Path, default=None)

    p.add_argument("--start", type=str, default=None, help="Optional start datetime for source candles.")
    p.add_argument("--end", type=str, default=None, help="Optional end datetime for source candles.")

    p.add_argument("--permission-windows-hours", type=str, default="48,72")
    p.add_argument("--entry-search-hours", type=float, default=24.0)
    p.add_argument("--m15-breakout-lookback", type=int, default=8)
    p.add_argument("--sl-lookback-m15", type=int, default=12)
    p.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    p.add_argument("--rr", type=float, default=1.5)
    p.add_argument("--horizon-hours", type=float, default=24.0)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")

    p.add_argument("--zigzag-depth", type=int, default=5)
    p.add_argument("--zigzag-deviation", type=float, default=3.0)
    p.add_argument("--zigzag-deviation-mode", choices=["price", "percent", "points"], default="price")
    p.add_argument("--zigzag-backstep", type=int, default=2)
    p.add_argument("--point-size", type=float, default=0.01)

    return p.parse_args()


def main() -> int:
    args = parse_args()
    windows_hours = parse_windows_hours(args.permission_windows_hours)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    start = parse_timestamp_or_none(args.start)
    end = parse_timestamp_or_none(args.end)

    print("[INFO] loading GOLD CSVs")
    h4_raw, h1_raw, m15_raw, m5_raw = load_gold_csvs(args)
    h4_raw = apply_time_filter(h4_raw, start=start, end=end)
    h1_raw = apply_time_filter(h1_raw, start=start, end=end)
    m15_raw = apply_time_filter(m15_raw, start=start, end=end)
    m5_raw = apply_time_filter(m5_raw, start=start, end=end)

    print(
        "[INFO] rows:",
        f"h4={len(h4_raw)}",
        f"h1={len(h1_raw)}",
        f"m15={len(m15_raw)}",
        f"m5={len(m5_raw)}",
    )

    print("[INFO] adding indicators: H4/H1/M15")
    h4 = add_fixed_rule_indicators(h4_raw, "H4", args)
    h1 = add_fixed_rule_indicators(h1_raw, "H1", args)
    m15 = add_fixed_rule_indicators(m15_raw, "M15", args)
    m5 = m5_raw.copy()
    m5["time"] = pd.to_datetime(m5["time"], errors="coerce")
    m5 = m5.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)

    print("[INFO] building H4 permission and H1 context events")
    h4_all, h4_events = build_h4_permission_frame(h4)
    h1_events = build_h1_context_events(h1)
    m15_triggers = build_m15_trigger_candidates(m15, args)
    m15_with_permission = add_h4_permission_to_triggers(m15_triggers, h4_all, h4_events, windows_hours)

    h1_events.to_csv(args.out_dir / "context_events_h1_regular_bullish_loose.csv", index=False, encoding="utf-8-sig")
    h4_events.to_csv(args.out_dir / "h4_regular_bullish_events.csv", index=False, encoding="utf-8-sig")
    m15_with_permission.to_csv(args.out_dir / "m15_trigger_candidates.csv", index=False, encoding="utf-8-sig")

    print(
        "[INFO] candidates:",
        f"h1_events={len(h1_events)}",
        f"h4_regular_events={len(h4_events)}",
        f"m15_triggers={len(m15_with_permission)}",
    )

    all_trades: list[pd.DataFrame] = []
    for window in windows_hours:
        print(f"[INFO] evaluating fixed rule: h4_permission_window={window}h")
        trades = build_trades_for_window(
            h1_events,
            m15_with_permission,
            m5,
            window_hours=window,
            args=args,
        )
        trades.to_csv(args.out_dir / f"fixed_rule_trades_{window}h.csv", index=False, encoding="utf-8-sig")
        if not trades.empty:
            all_trades.append(trades)

    if all_trades:
        trades_all = pd.concat(all_trades, ignore_index=True)
    else:
        trades_all = pd.DataFrame()

    summary = summarize_trades(trades_all)
    monthly = summarize_monthly(trades_all)
    equity = build_equity_curve(trades_all)

    summary.to_csv(args.out_dir / "fixed_rule_summary.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(args.out_dir / "fixed_rule_monthly.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(args.out_dir / "fixed_rule_equity_curve.csv", index=False, encoding="utf-8-sig")

    if 48 in windows_hours and 72 in windows_hours:
        p48 = args.out_dir / "fixed_rule_trades_48h.csv"
        p72 = args.out_dir / "fixed_rule_trades_72h.csv"
        if p48.exists() and p72.exists():
            t48 = pd.read_csv(p48, encoding="utf-8-sig")
            t72 = pd.read_csv(p72, encoding="utf-8-sig")
            if not t72.empty:
                keys48 = set(t48["h1_event_id"].astype(str) + "|" + t48["entry_time"].astype(str)) if not t48.empty else set()
                t72["_cmp_key"] = t72["h1_event_id"].astype(str) + "|" + t72["entry_time"].astype(str)
                extra = t72[~t72["_cmp_key"].isin(keys48)].drop(columns=["_cmp_key"], errors="ignore")
            else:
                extra = pd.DataFrame()
            extra.to_csv(args.out_dir / "extra_trades_added_by_72h.csv", index=False, encoding="utf-8-sig")

    write_readme(args, args.out_dir, windows_hours)

    print("[INFO] summary")
    if summary.empty:
        print("  no trades")
    else:
        print(summary.to_string(index=False))
    print(f"[INFO] wrote: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

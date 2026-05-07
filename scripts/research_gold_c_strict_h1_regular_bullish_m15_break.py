#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only GOLD C_STRICT + H1 regular bullish + M15 break validation.

This script is deliberately separated from Mochipoyo live/demo/autotrade code.
It reads copied research CSV snapshots only and writes research result CSVs only.
It never writes to MT5 source CSVs, trigger state, ledgers, Discord payloads, or
order-intent files.

Condition ID:
    GOLD_C_STRICT_H1_REGULAR_BULLISH_M15_BREAK_48H

Rule:
    BUY only.

    H4 C_STRICT permission:
        Latest confirmed H4 regular bullish divergence must be within 48 hours
        at the M15 entry close time.
        H4 env_up alone is NOT used.

    H1 context:
        Newly confirmed H1 regular bullish divergence, and
        close < ema50 OR ema20 < ema50 at confirmation.

    M15 trigger:
        First M15 trigger within 24 hours after H1 confirmation:
          close > high.shift(1).rolling(8).max()
          close > ema20
          MACD(6,13,4) > signal
          macd_hist > previous macd_hist

    Entry/exit:
        Entry = M15 close at M15 close_time.
        SL = M15 rolling low(12) - ATR14 * 0.05.
        TP = entry + risk * 1.5.
        Outcome = M5 first-touch, 24h horizon, same-M5-bar TP/SL = SL loss.

Outputs:
    data_coverage.csv
    context_h4_regular_bullish_events.csv
    context_h1_regular_bullish_events.csv
    m15_trigger_candidates.csv
    trades_all_candidates.csv
    trades_evaluated_only.csv
    trades_no_m5_path.csv
    summary_all_candidates.csv
    summary_evaluated_only.csv
    monthly_evaluated_only.csv

Example:
    python scripts\research_gold_c_strict_h1_regular_bullish_m15_break.py ^
      --csv-dir data\research_csv_snapshots\gold_cb_20260508_01 ^
      --out-dir data\research_results\gold_c_strict_h1_regular_bullish_m15_break_48h
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

CONDITION_ID = "GOLD_C_STRICT_H1_REGULAR_BULLISH_M15_BREAK_48H"
SYMBOL = "GOLD"
DIRECTION = "BUY"

TIMEFRAME_MINUTES: dict[str, int] = {
    "M5": 5,
    "M15": 15,
    "H1": 60,
    "H4": 240,
}

REQUIRED_FILES: dict[str, str] = {
    "H4": "goldsharp_h4.csv",
    "H1": "goldsharp_h1.csv",
    "M15": "goldsharp_m15.csv",
    "M5": "goldsharp_m5.csv",
}

EVALUATED_OUTCOMES = {"WIN", "LOSS", "TIMEOUT"}
NON_EVALUATED_OUTCOMES = {"NO_M5_PATH", "INVALID_RISK"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Research-only GOLD C_STRICT H1 regular bullish M15 break validation."
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        required=True,
        help="Copied research CSV snapshot directory containing goldsharp_h4/h1/m15/m5 CSVs.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_c_strict_h1_regular_bullish_m15_break_48h"),
        help="Research-only output directory.",
    )
    parser.add_argument("--h4-permission-hours", type=float, default=48.0)
    parser.add_argument("--h1-entry-search-hours", type=float, default=24.0)
    parser.add_argument("--outcome-horizon-hours", type=float, default=24.0)
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--m15-breakout-lookback", type=int, default=8)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=1.5)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return parser.parse_args()


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_ohlc_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path, sep=sniff_sep(path), encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(
        columns={
            "datetime": "time",
            "date": "time",
            "timestamp": "time",
            "tickvolume": "tick_volume",
            "tick volume": "tick_volume",
            "volume": "tick_volume",
        }
    )

    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing columns in {path}: {missing}; columns={list(df.columns)}")

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)
    df = df.sort_values("time", kind="mergesort").drop_duplicates(subset=["time"], keep="last")
    return df.reset_index(drop=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def timeframe_minutes(tf: str) -> int:
    key = str(tf).upper()
    if key not in TIMEFRAME_MINUTES:
        raise ValueError(f"Unsupported timeframe: {tf}")
    return TIMEFRAME_MINUTES[key]


def safe_float(value: object, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def add_indicators(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["close_time"] = out["time"] + pd.to_timedelta(timeframe_minutes(tf), unit="m")
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["atr14"] = atr14(out)
    out["macd"] = ema(out["close"], 6) - ema(out["close"], 13)
    out["macd_signal"] = ema(out["macd"], 4)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    return out


def load_research_csvs(csv_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for tf, filename in REQUIRED_FILES.items():
        frames[tf] = read_ohlc_csv(csv_dir / filename)
    return frames


def build_data_coverage(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for tf, filename in REQUIRED_FILES.items():
        df = frames[tf]
        rows.append(
            {
                "condition_id": CONDITION_ID,
                "timeframe": tf,
                "file_name": filename,
                "rows": int(len(df)),
                "time_min": df["time"].min(),
                "time_max": df["time"].max(),
                "columns": ",".join(map(str, df.columns)),
            }
        )
    return pd.DataFrame(rows)


def detect_pivot_lows(df: pd.DataFrame, *, left: int, right: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    lows = df["low"].to_numpy(dtype=float)
    for i in range(left, len(df) - right):
        value = lows[i]
        if not math.isfinite(value):
            continue
        left_window = lows[i - left : i]
        right_window = lows[i + 1 : i + right + 1]
        if np.all(value < left_window) and np.all(value < right_window):
            confirm_idx = i + right
            rows.append(
                {
                    "pivot_idx": i,
                    "confirm_idx": confirm_idx,
                    "pivot_time": df.at[i, "time"],
                    "pivot_confirm_time": df.at[confirm_idx, "close_time"],
                    "pivot_low": df.at[i, "low"],
                    "pivot_macd": df.at[i, "macd"],
                    "close_at_confirm": df.at[confirm_idx, "close"],
                    "ema20_at_confirm": df.at[confirm_idx, "ema20"],
                    "ema50_at_confirm": df.at[confirm_idx, "ema50"],
                    "atr14_at_confirm": df.at[confirm_idx, "atr14"],
                    "macd_at_confirm": df.at[confirm_idx, "macd"],
                    "macd_signal_at_confirm": df.at[confirm_idx, "macd_signal"],
                    "macd_hist_at_confirm": df.at[confirm_idx, "macd_hist"],
                }
            )
    return pd.DataFrame(rows)


def detect_regular_bullish_events(pivots: pd.DataFrame, *, tf: str) -> pd.DataFrame:
    if pivots.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    piv = pivots.sort_values("pivot_confirm_time", kind="mergesort").reset_index(drop=True)
    for i in range(1, len(piv)):
        prev = piv.iloc[i - 1]
        cur = piv.iloc[i]
        cur_low = safe_float(cur["pivot_low"])
        prev_low = safe_float(prev["pivot_low"])
        cur_macd = safe_float(cur["pivot_macd"])
        prev_macd = safe_float(prev["pivot_macd"])
        if not all(math.isfinite(v) for v in [cur_low, prev_low, cur_macd, prev_macd]):
            continue
        if cur_low < prev_low and cur_macd > prev_macd:
            prefix = tf.lower()
            rows.append(
                {
                    "condition_id": CONDITION_ID,
                    f"{prefix}_event_id": f"{tf}_REG_BULL_{pd.Timestamp(cur['pivot_confirm_time']).strftime('%Y%m%d%H%M')}_{i:05d}",
                    f"{prefix}_pivot_time": cur["pivot_time"],
                    f"{prefix}_pivot_confirm_time": cur["pivot_confirm_time"],
                    f"{prefix}_pivot_low": cur_low,
                    f"{prefix}_prev_pivot_time": prev["pivot_time"],
                    f"{prefix}_prev_pivot_low": prev_low,
                    f"{prefix}_pivot_macd": cur_macd,
                    f"{prefix}_prev_pivot_macd": prev_macd,
                    f"{prefix}_close_at_confirm": cur["close_at_confirm"],
                    f"{prefix}_ema20_at_confirm": cur["ema20_at_confirm"],
                    f"{prefix}_ema50_at_confirm": cur["ema50_at_confirm"],
                    f"{prefix}_atr14_at_confirm": cur["atr14_at_confirm"],
                    f"{prefix}_macd_at_confirm": cur["macd_at_confirm"],
                    f"{prefix}_macd_signal_at_confirm": cur["macd_signal_at_confirm"],
                    f"{prefix}_macd_hist_at_confirm": cur["macd_hist_at_confirm"],
                }
            )
    return pd.DataFrame(rows)


def build_h4_events(h4: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    pivots = detect_pivot_lows(h4, left=args.pivot_left, right=args.pivot_right)
    events = detect_regular_bullish_events(pivots, tf="H4")
    if events.empty:
        return pd.DataFrame(
            columns=[
                "condition_id",
                "h4_event_id",
                "h4_pivot_time",
                "h4_pivot_confirm_time",
                "h4_pivot_low",
                "h4_prev_pivot_time",
                "h4_prev_pivot_low",
                "h4_pivot_macd",
                "h4_prev_pivot_macd",
                "h4_close_at_confirm",
                "h4_ema20_at_confirm",
                "h4_ema50_at_confirm",
                "h4_macd_hist_at_confirm",
            ]
        )
    return events.sort_values("h4_pivot_confirm_time", kind="mergesort").reset_index(drop=True)


def build_h1_events(h1: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    pivots = detect_pivot_lows(h1, left=args.pivot_left, right=args.pivot_right)
    events = detect_regular_bullish_events(pivots, tf="H1")
    if events.empty:
        return pd.DataFrame()

    events["h1_exhaustion_ok"] = (
        pd.to_numeric(events["h1_close_at_confirm"], errors="coerce")
        < pd.to_numeric(events["h1_ema50_at_confirm"], errors="coerce")
    ) | (
        pd.to_numeric(events["h1_ema20_at_confirm"], errors="coerce")
        < pd.to_numeric(events["h1_ema50_at_confirm"], errors="coerce")
    )
    events = events[events["h1_exhaustion_ok"]].copy()
    return events.sort_values("h1_pivot_confirm_time", kind="mergesort").reset_index(drop=True)


def build_m15_trigger_base(m15: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = m15.copy()
    out["m15_rolling_high_8_prev"] = out["high"].shift(1).rolling(
        args.m15_breakout_lookback, min_periods=args.m15_breakout_lookback
    ).max()
    out["m15_sl_base_low"] = out["low"].rolling(
        args.sl_lookback_m15, min_periods=args.sl_lookback_m15
    ).min()
    out["m15_trigger_ok_base"] = (
        (out["close"] > out["m15_rolling_high_8_prev"])
        & (out["close"] > out["ema20"])
        & (out["macd"] > out["macd_signal"])
        & (out["macd_hist"] > out["macd_hist"].shift(1))
        & out["m15_sl_base_low"].notna()
        & out["atr14"].notna()
    )
    out = out[out["m15_trigger_ok_base"]].copy()
    out["condition_id"] = CONDITION_ID
    out["m15_time"] = out["time"]
    out["m15_close_time"] = out["close_time"]
    out["m15_open"] = out["open"]
    out["m15_high"] = out["high"]
    out["m15_low"] = out["low"]
    out["m15_close"] = out["close"]
    out["m15_ema20"] = out["ema20"]
    out["m15_ema50"] = out["ema50"]
    out["m15_atr14"] = out["atr14"]
    out["m15_macd"] = out["macd"]
    out["m15_macd_signal"] = out["macd_signal"]
    out["m15_macd_hist"] = out["macd_hist"]
    return out[
        [
            "condition_id",
            "m15_time",
            "m15_close_time",
            "m15_open",
            "m15_high",
            "m15_low",
            "m15_close",
            "m15_ema20",
            "m15_ema50",
            "m15_atr14",
            "m15_macd",
            "m15_macd_signal",
            "m15_macd_hist",
            "m15_rolling_high_8_prev",
            "m15_sl_base_low",
            "m15_trigger_ok_base",
        ]
    ].reset_index(drop=True)


def latest_h4_event_before(h4_events: pd.DataFrame, ts: pd.Timestamp) -> pd.Series | None:
    if h4_events.empty:
        return None
    eligible = h4_events[h4_events["h4_pivot_confirm_time"] <= ts]
    if eligible.empty:
        return None
    return eligible.sort_values("h4_pivot_confirm_time", kind="mergesort").iloc[-1]


def first_m15_trigger_for_h1_event(
    h1_event: pd.Series,
    h4_events: pd.DataFrame,
    m15_base: pd.DataFrame,
    args: argparse.Namespace,
) -> dict[str, object] | None:
    h1_confirm = pd.Timestamp(h1_event["h1_pivot_confirm_time"])
    search_end = h1_confirm + pd.to_timedelta(args.h1_entry_search_hours, unit="h")
    candidates = m15_base[
        (m15_base["m15_close_time"] >= h1_confirm)
        & (m15_base["m15_close_time"] <= search_end)
    ].copy()
    if candidates.empty:
        return None

    for _, m15_row in candidates.sort_values("m15_close_time", kind="mergesort").iterrows():
        m15_close_time = pd.Timestamp(m15_row["m15_close_time"])
        h4_event = latest_h4_event_before(h4_events, m15_close_time)
        if h4_event is None:
            continue
        h4_confirm = pd.Timestamp(h4_event["h4_pivot_confirm_time"])
        age_hours = (m15_close_time - h4_confirm).total_seconds() / 3600.0
        if 0.0 <= age_hours <= float(args.h4_permission_hours):
            out: dict[str, object] = {**h1_event.to_dict(), **m15_row.to_dict()}
            out.update(h4_event.to_dict())
            out["h4_permission_age_hours"] = age_hours
            out["h4_permission_ok"] = True
            out["trigger_ok"] = True
            return out
    return None


def build_trade_candidates(
    h1_events: pd.DataFrame,
    h4_events: pd.DataFrame,
    m15_base: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, h1_event in h1_events.sort_values("h1_pivot_confirm_time", kind="mergesort").iterrows():
        trigger = first_m15_trigger_for_h1_event(h1_event, h4_events, m15_base, args)
        if trigger is None:
            continue

        entry_price = safe_float(trigger["m15_close"])
        sl_base_low = safe_float(trigger["m15_sl_base_low"])
        atr = safe_float(trigger["m15_atr14"])
        sl_price = sl_base_low - atr * float(args.sl_atr_buffer_mult)
        risk = entry_price - sl_price
        if not all(math.isfinite(v) for v in [entry_price, sl_price, risk]) or risk <= 0:
            outcome = "INVALID_RISK"
            tp_price = np.nan
        else:
            outcome = "PENDING"
            tp_price = entry_price + risk * float(args.rr)

        entry_time = pd.Timestamp(trigger["m15_close_time"])
        row = {
            "condition_id": CONDITION_ID,
            "symbol": SYMBOL,
            "direction": DIRECTION,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "risk_price": risk,
            "rr": float(args.rr),
            "initial_outcome": outcome,
            **trigger,
        }
        row["trade_key"] = (
            f"{CONDITION_ID}|{row.get('h4_event_id','')}|{row.get('h1_event_id','')}|"
            f"{entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def judge_buy_first_touch(
    m5: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk: float,
    horizon_hours: float,
    inbar_priority: str,
) -> dict[str, object]:
    if not all(math.isfinite(v) for v in [entry_price, sl_price, tp_price, risk]) or risk <= 0:
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

    checked = 0
    for _, bar in path.sort_values("time", kind="mergesort").iterrows():
        checked += 1
        hit_sl = safe_float(bar["low"]) <= sl_price
        hit_tp = safe_float(bar["high"]) >= tp_price
        if hit_sl and hit_tp:
            if str(inbar_priority).upper() == "TP":
                return {
                    "outcome": "WIN",
                    "exit_time": bar["time"],
                    "exit_price": tp_price,
                    "realized_r": (tp_price - entry_price) / risk,
                    "bars_checked": checked,
                }
            return {
                "outcome": "LOSS",
                "exit_time": bar["time"],
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": checked,
            }
        if hit_sl:
            return {
                "outcome": "LOSS",
                "exit_time": bar["time"],
                "exit_price": sl_price,
                "realized_r": -1.0,
                "bars_checked": checked,
            }
        if hit_tp:
            return {
                "outcome": "WIN",
                "exit_time": bar["time"],
                "exit_price": tp_price,
                "realized_r": (tp_price - entry_price) / risk,
                "bars_checked": checked,
            }

    last = path.sort_values("time", kind="mergesort").iloc[-1]
    exit_price = safe_float(last["close"])
    return {
        "outcome": "TIMEOUT",
        "exit_time": last["time"],
        "exit_price": exit_price,
        "realized_r": (exit_price - entry_price) / risk,
        "bars_checked": checked,
    }


def evaluate_trades(trades: pd.DataFrame, m5: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()

    rows: list[dict[str, object]] = []
    m5 = m5.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    for _, row in trades.iterrows():
        if str(row.get("initial_outcome")) == "INVALID_RISK":
            result = {
                "outcome": "INVALID_RISK",
                "exit_time": pd.NaT,
                "exit_price": np.nan,
                "realized_r": np.nan,
                "bars_checked": 0,
            }
        else:
            result = judge_buy_first_touch(
                m5,
                entry_time=pd.Timestamp(row["entry_time"]),
                entry_price=safe_float(row["entry_price"]),
                sl_price=safe_float(row["sl_price"]),
                tp_price=safe_float(row["tp_price"]),
                risk=safe_float(row["risk_price"]),
                horizon_hours=float(args.outcome_horizon_hours),
                inbar_priority=str(args.inbar_priority),
            )
        out = row.to_dict()
        out.update(result)
        rows.append(out)

    out_df = pd.DataFrame(rows).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    out_df["entry_month"] = pd.to_datetime(out_df["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    out_df["is_evaluated"] = out_df["outcome"].isin(EVALUATED_OUTCOMES)
    return out_df


def max_drawdown_r(r_values: pd.Series) -> float:
    r = pd.to_numeric(r_values, errors="coerce").dropna()
    if r.empty:
        return 0.0
    equity = r.cumsum()
    peak = equity.cummax()
    return float((peak - equity).max())


def profit_factor(r_values: pd.Series) -> float:
    r = pd.to_numeric(r_values, errors="coerce").dropna()
    if r.empty:
        return float("nan")
    gross_profit = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else float("nan")
    return gross_profit / gross_loss


def summarize_all_candidates(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(
            [
                {
                    "condition_id": CONDITION_ID,
                    "all_candidates": 0,
                    "evaluated_candidates": 0,
                    "no_m5_path": 0,
                    "invalid_risk": 0,
                }
            ]
        )
    return pd.DataFrame(
        [
            {
                "condition_id": CONDITION_ID,
                "all_candidates": int(len(trades)),
                "evaluated_candidates": int(trades["outcome"].isin(EVALUATED_OUTCOMES).sum()),
                "wins": int((trades["outcome"] == "WIN").sum()),
                "losses": int((trades["outcome"] == "LOSS").sum()),
                "timeouts": int((trades["outcome"] == "TIMEOUT").sum()),
                "no_m5_path": int((trades["outcome"] == "NO_M5_PATH").sum()),
                "invalid_risk": int((trades["outcome"] == "INVALID_RISK").sum()),
                "first_entry_time": trades["entry_time"].min(),
                "last_entry_time": trades["entry_time"].max(),
            }
        ]
    )


def summarize_evaluated(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame(
            [
                {
                    "condition_id": CONDITION_ID,
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "timeouts": 0,
                    "win_rate": np.nan,
                    "total_r": 0.0,
                    "avg_r": np.nan,
                    "pf": np.nan,
                    "max_dd_r": 0.0,
                    "first_entry_time": "",
                    "last_entry_time": "",
                    "months_with_trades": 0,
                }
            ]
        )

    r = pd.to_numeric(trades_eval["realized_r"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "condition_id": CONDITION_ID,
                "trades": int(len(trades_eval)),
                "wins": int((trades_eval["outcome"] == "WIN").sum()),
                "losses": int((trades_eval["outcome"] == "LOSS").sum()),
                "timeouts": int((trades_eval["outcome"] == "TIMEOUT").sum()),
                "win_rate": float((trades_eval["outcome"] == "WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "first_entry_time": trades_eval["entry_time"].min(),
                "last_entry_time": trades_eval["entry_time"].max(),
                "months_with_trades": int(trades_eval["entry_month"].nunique()),
            }
        ]
    )


def summarize_monthly(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame(
            columns=[
                "condition_id",
                "entry_month",
                "trades",
                "wins",
                "losses",
                "timeouts",
                "win_rate",
                "total_r",
                "avg_r",
                "pf",
                "max_dd_r",
            ]
        )

    rows: list[dict[str, object]] = []
    for month, group in trades_eval.groupby("entry_month", dropna=False):
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        rows.append(
            {
                "condition_id": CONDITION_ID,
                "entry_month": str(month),
                "trades": int(len(group)),
                "wins": int((group["outcome"] == "WIN").sum()),
                "losses": int((group["outcome"] == "LOSS").sum()),
                "timeouts": int((group["outcome"] == "TIMEOUT").sum()),
                "win_rate": float((group["outcome"] == "WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
            }
        )
    return pd.DataFrame(rows).sort_values("entry_month", kind="mergesort").reset_index(drop=True)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] condition_id={CONDITION_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print("[INFO] loading copied research CSVs")
    frames = load_research_csvs(args.csv_dir)
    write_csv(build_data_coverage(frames), args.out_dir / "data_coverage.csv")

    print("[INFO] adding indicators")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    print("[INFO] detecting H4/H1 regular bullish divergence events")
    h4_events = build_h4_events(h4, args)
    h1_events = build_h1_events(h1, args)
    write_csv(h4_events, args.out_dir / "context_h4_regular_bullish_events.csv")
    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")

    print("[INFO] building M15 trigger base")
    m15_base = build_m15_trigger_base(m15, args)

    print("[INFO] building trade candidates with strict H4 48h permission")
    trades_pending = build_trade_candidates(h1_events, h4_events, m15_base, args)
    if not trades_pending.empty:
        trigger_cols = [
            "condition_id",
            "h1_event_id",
            "h4_event_id",
            "m15_time",
            "m15_close_time",
            "m15_close",
            "m15_ema20",
            "m15_atr14",
            "m15_macd",
            "m15_macd_signal",
            "m15_macd_hist",
            "m15_rolling_high_8_prev",
            "h1_pivot_confirm_time",
            "h4_pivot_confirm_time",
            "h4_permission_age_hours",
            "h4_permission_ok",
            "trigger_ok",
        ]
        write_csv(
            trades_pending[[c for c in trigger_cols if c in trades_pending.columns]],
            args.out_dir / "m15_trigger_candidates.csv",
        )
    else:
        write_csv(pd.DataFrame(), args.out_dir / "m15_trigger_candidates.csv")

    print("[INFO] evaluating trades by M5 first-touch")
    trades_all = evaluate_trades(trades_pending, m5, args) if not trades_pending.empty else pd.DataFrame()
    trades_eval = trades_all[trades_all["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not trades_all.empty else pd.DataFrame()
    trades_no_m5 = trades_all[trades_all["outcome"].eq("NO_M5_PATH")].copy() if not trades_all.empty else pd.DataFrame()

    write_csv(trades_all, args.out_dir / "trades_all_candidates.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only.csv")
    write_csv(trades_no_m5, args.out_dir / "trades_no_m5_path.csv")
    write_csv(summarize_all_candidates(trades_all), args.out_dir / "summary_all_candidates.csv")
    write_csv(summarize_evaluated(trades_eval), args.out_dir / "summary_evaluated_only.csv")
    write_csv(summarize_monthly(trades_eval), args.out_dir / "monthly_evaluated_only.csv")

    print("[INFO] completed")
    print(f"[INFO] h4_events={len(h4_events)} h1_events={len(h1_events)}")
    print(f"[INFO] all_candidates={len(trades_all)} evaluated={len(trades_eval)} no_m5_path={len(trades_no_m5)}")
    summary = summarize_evaluated(trades_eval)
    print(summary.to_string(index=False))
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

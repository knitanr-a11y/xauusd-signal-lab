#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only GOLD bearish A/B classifier backtest.

This script is deliberately separated from the existing Mochipoyo and
GOLD C_ENV BUY live/autotrade flows.

It validates this SELL-only design:

A improved:
    H1:
      close < EMA20
      EMA20 < EMA50
      EMA20 slope3 < 0
      (EMA20 - close) / ATR14 <= 1.60
    H4:
      close < EMA20
      EMA20 < EMA50
    D1:
      close < EMA20
    M15:
      low < previous rolling low 16
      close_pos <= 0.45
      MACD hist delta < 0
      range / ATR14 >= 0.90

B improved:
    H1:
      close < EMA50
      EMA20 < EMA50
      (EMA20 - close) / ATR14 <= 1.60
    H4:
      EMA20 < EMA50
    D1:
      close < EMA20
    M15:
      low < previous rolling low 6
      close_pos <= 0.50
      MACD hist < 0
      MACD hist delta < 0

Final rank:
    CORE_AB_CONFIRM: A and B, trade_enabled=True, lot_multiplier=2.0
    B_ONLY_SAFE: B and not A, trade_enabled=True, lot_multiplier=1.0
    A_ONLY_OBSERVE: A and not B, trade_enabled=False, lot_multiplier=0.0

Entry/exit:
    signal is evaluated on a confirmed M15 bar.
    entry_time = next M15 bar open time.
    entry_price = next M15 bar open.
    SELL SL = entry + 10.0
    SELL TP = entry - 20.0
    M1 first-touch, 12h horizon, SL priority on same M1 bar conflict.

Outputs:
    data_coverage.csv
    signals_all_raw.csv
    signals_trade_enabled_raw.csv
    trades_classified_cooldown.csv
    summary_by_rank.csv
    summary_overall_lot_weighted.csv
    monthly_by_rank.csv
    target_window_20260428.csv
    latest_signal_preview.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CONDITION_FAMILY_ID = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"
CONDITION_ID_CORE = "GOLD_H1H4_BEAR_M15_LOW_BREAK_CORE_AB_CONFIRM_FIXED10_RR2_12H"
CONDITION_ID_B_ONLY = "GOLD_H1H4_BEAR_M15_LOW_BREAK_B_ONLY_SAFE_FIXED10_RR2_12H"
CONDITION_ID_A_ONLY = "GOLD_H1H4_BEAR_M15_LOW_BREAK_A_ONLY_OBSERVE_FIXED10_RR2_12H"

SYMBOL = "GOLD"
DIRECTION = "SELL"

TIMEFRAME_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

REQUIRED_FILES = {
    "D1": "goldsharp_d1.csv",
    "H4": "goldsharp_h4.csv",
    "H1": "goldsharp_h1.csv",
    "M15": "goldsharp_m15.csv",
    "M1": "goldsharp_m1.csv",
}

LEDGER_COLUMNS = [
    "created_at_utc",
    "signal_key",
    "condition_family_id",
    "condition_id",
    "symbol",
    "direction",
    "rank",
    "signal_group",
    "signal_time",
    "entry_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "risk_price",
    "reward_price",
    "rr",
    "max_hold_hours",
    "a_pass",
    "b_pass",
    "trade_enabled",
    "base_lot",
    "lot_multiplier",
    "effective_lot",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research-only GOLD bearish A/B classifier backtest.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_h1h4_bear_m15_low_break_ab_classifier"),
    )
    parser.add_argument("--sl-usd", type=float, default=10.0)
    parser.add_argument("--tp-usd", type=float, default=20.0)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--horizon-hours", type=float, default=12.0)
    parser.add_argument("--cooldown-bars-m15", type=int, default=8)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument("--base-lot", type=float, default=0.10)
    parser.add_argument("--core-lot-multiplier", type=float, default=2.0)
    parser.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    parser.add_argument("--max-lot-per-trade", type=float, default=99.0)
    parser.add_argument("--target-start", type=str, default="2026-04-28 07:00:00")
    parser.add_argument("--target-end", type=str, default="2026-04-28 14:00:00")
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
    return df.sort_values("time", kind="mergesort").drop_duplicates("time", keep="last").reset_index(drop=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


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


def rsi14(close: pd.Series) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(14, min_periods=14).mean()
    avg_loss = loss.rolling(14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def add_indicators(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["close_time"] = out["time"] + pd.to_timedelta(TIMEFRAME_MINUTES[tf], unit="m")
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["atr14"] = atr14(out)
    out["rsi14"] = rsi14(out["close"])
    out["macd"] = ema(out["close"], 6) - ema(out["close"], 13)
    out["macd_signal"] = ema(out["macd"], 4)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["macd_hist_delta"] = out["macd_hist"] - out["macd_hist"].shift(1)
    out["range"] = out["high"] - out["low"]
    out["close_pos"] = np.where(out["range"] > 0, (out["close"] - out["low"]) / out["range"], np.nan)
    out["range_atr_ratio"] = out["range"] / out["atr14"]
    out["ema20_slope3"] = out["ema20"] - out["ema20"].shift(3)
    out["dist_e20_atr_sell"] = (out["ema20"] - out["close"]) / out["atr14"]
    return out


def load_frames(csv_dir: Path) -> dict[str, pd.DataFrame]:
    return {tf: read_ohlc_csv(csv_dir / filename) for tf, filename in REQUIRED_FILES.items()}


def build_data_coverage(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for tf, filename in REQUIRED_FILES.items():
        df = frames[tf]
        rows.append(
            {
                "condition_family_id": CONDITION_FAMILY_ID,
                "timeframe": tf,
                "file_name": filename,
                "rows": int(len(df)),
                "time_min": df["time"].min(),
                "time_max": df["time"].max(),
                "columns": ",".join(map(str, df.columns)),
            }
        )
    return pd.DataFrame(rows)


def prefix_context(df: pd.DataFrame, tf: str, columns: list[str]) -> pd.DataFrame:
    use = ["close_time"] + columns
    out = df[use].copy().sort_values("close_time", kind="mergesort")
    out = out.rename(columns={"close_time": f"{tf.lower()}_close_time"})
    for col in columns:
        out = out.rename(columns={col: f"{tf.lower()}_{col}"})
    return out


def attach_context(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    base = m15.copy().sort_values("close_time", kind="mergesort").reset_index(drop=True)

    h1_ctx = prefix_context(
        h1,
        "H1",
        ["open", "high", "low", "close", "ema20", "ema50", "atr14", "macd", "macd_signal", "macd_hist", "macd_hist_delta", "ema20_slope3", "dist_e20_atr_sell"],
    )
    h4_ctx = prefix_context(
        h4,
        "H4",
        ["open", "high", "low", "close", "ema20", "ema50", "atr14", "macd", "macd_signal", "macd_hist", "ema20_slope3"],
    )
    d1_ctx = prefix_context(
        d1,
        "D1",
        ["open", "high", "low", "close", "ema20", "ema50", "atr14", "rsi14", "macd", "macd_signal", "macd_hist"],
    )

    out = pd.merge_asof(base, h1_ctx, left_on="close_time", right_on="h1_close_time", direction="backward")
    out = pd.merge_asof(out, h4_ctx, left_on="close_time", right_on="h4_close_time", direction="backward")
    out = pd.merge_asof(out, d1_ctx, left_on="close_time", right_on="d1_close_time", direction="backward")
    return out


def build_signal_candidates(m15_ctx: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = m15_ctx.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["m15_prev_low16"] = out["low"].shift(1).rolling(16, min_periods=16).min()
    out["m15_prev_low6"] = out["low"].shift(1).rolling(6, min_periods=6).min()

    a_h1 = (
        (out["h1_close"] < out["h1_ema20"])
        & (out["h1_ema20"] < out["h1_ema50"])
        & (out["h1_ema20_slope3"] < 0)
        & (out["h1_dist_e20_atr_sell"] <= 1.60)
    )
    a_h4 = (out["h4_close"] < out["h4_ema20"]) & (out["h4_ema20"] < out["h4_ema50"])
    d1_bear = out["d1_close"] < out["d1_ema20"]
    a_m15 = (
        (out["low"] < out["m15_prev_low16"])
        & (out["close_pos"] <= 0.45)
        & (out["macd_hist_delta"] < 0)
        & (out["range_atr_ratio"] >= 0.90)
    )

    b_h1 = (
        (out["h1_close"] < out["h1_ema50"])
        & (out["h1_ema20"] < out["h1_ema50"])
        & (out["h1_dist_e20_atr_sell"] <= 1.60)
    )
    b_h4 = out["h4_ema20"] < out["h4_ema50"]
    b_m15 = (
        (out["low"] < out["m15_prev_low6"])
        & (out["close_pos"] <= 0.50)
        & (out["macd_hist"] < 0)
        & (out["macd_hist_delta"] < 0)
    )

    out["a_pass"] = (a_h1 & a_h4 & d1_bear & a_m15).fillna(False)
    out["b_pass"] = (b_h1 & b_h4 & d1_bear & b_m15).fillna(False)
    out["rank"] = np.select(
        [out["a_pass"] & out["b_pass"], out["b_pass"] & ~out["a_pass"], out["a_pass"] & ~out["b_pass"]],
        ["CORE_AB_CONFIRM", "B_ONLY_SAFE", "A_ONLY_OBSERVE"],
        default="NO_SIGNAL",
    )
    out["trade_enabled"] = out["rank"].isin(["CORE_AB_CONFIRM", "B_ONLY_SAFE"])
    out["condition_id"] = np.select(
        [out["rank"].eq("CORE_AB_CONFIRM"), out["rank"].eq("B_ONLY_SAFE"), out["rank"].eq("A_ONLY_OBSERVE")],
        [CONDITION_ID_CORE, CONDITION_ID_B_ONLY, CONDITION_ID_A_ONLY],
        default="",
    )
    out["signal_group"] = out["rank"]

    raw = out[out["rank"] != "NO_SIGNAL"].copy()
    if raw.empty:
        return raw

    next_open = out[["time", "open"]].rename(columns={"time": "entry_time", "open": "entry_price"})
    raw["entry_time"] = raw["close_time"]
    raw = raw.merge(next_open, on="entry_time", how="left")
    raw = raw[raw["entry_price"].notna()].copy()

    raw["symbol"] = SYMBOL
    raw["direction"] = DIRECTION
    raw["signal_time"] = raw["time"]
    raw["m15_close_time"] = raw["close_time"]
    raw["sl_price"] = raw["entry_price"] + float(args.sl_usd)
    raw["tp_price"] = raw["entry_price"] - float(args.tp_usd)
    raw["risk_price"] = float(args.sl_usd)
    raw["reward_price"] = float(args.tp_usd)
    raw["rr"] = float(args.rr)
    raw["max_hold_hours"] = float(args.horizon_hours)
    raw["base_lot"] = float(args.base_lot)
    raw["lot_multiplier"] = np.select(
        [raw["rank"].eq("CORE_AB_CONFIRM"), raw["rank"].eq("B_ONLY_SAFE")],
        [float(args.core_lot_multiplier), float(args.standard_lot_multiplier)],
        default=0.0,
    )
    raw["effective_lot"] = np.minimum(raw["base_lot"] * raw["lot_multiplier"], float(args.max_lot_per_trade))
    raw.loc[~raw["trade_enabled"], "effective_lot"] = 0.0

    return raw.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def apply_common_cooldown(signals: pd.DataFrame, cooldown_bars_m15: int) -> pd.DataFrame:
    if signals.empty:
        return signals.copy()
    trade_signals = signals[signals["trade_enabled"]].copy().sort_values("entry_time", kind="mergesort")
    cooldown_minutes = int(cooldown_bars_m15) * 15
    accepted = []
    last_entry_time: pd.Timestamp | None = None
    for _, row in trade_signals.iterrows():
        et = pd.Timestamp(row["entry_time"])
        if last_entry_time is None or et >= last_entry_time + pd.to_timedelta(cooldown_minutes, unit="m"):
            accepted.append(row.to_dict())
            last_entry_time = et
    accepted_df = pd.DataFrame(accepted)
    if accepted_df.empty:
        return pd.DataFrame(columns=signals.columns)
    return accepted_df.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def judge_sell_first_touch(
    m1: pd.DataFrame,
    *,
    entry_time: pd.Timestamp,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk: float,
    horizon_hours: float,
    inbar_priority: str,
) -> dict[str, Any]:
    if not all(math.isfinite(v) for v in [entry_price, sl_price, tp_price, risk]) or risk <= 0:
        return {"outcome": "INVALID_RISK", "exit_time": pd.NaT, "exit_price": np.nan, "realized_r": np.nan, "bars_checked": 0}

    end_time = entry_time + pd.to_timedelta(horizon_hours, unit="h")
    path = m1[(m1["time"] >= entry_time) & (m1["time"] < end_time)].copy()
    if path.empty:
        return {"outcome": "NO_M1_PATH", "exit_time": pd.NaT, "exit_price": np.nan, "realized_r": np.nan, "bars_checked": 0}

    checked = 0
    for _, bar in path.sort_values("time", kind="mergesort").iterrows():
        checked += 1
        hit_sl = safe_float(bar["high"]) >= sl_price
        hit_tp = safe_float(bar["low"]) <= tp_price
        if hit_sl and hit_tp:
            if str(inbar_priority).upper() == "TP":
                return {"outcome": "WIN", "exit_time": bar["time"], "exit_price": tp_price, "realized_r": (entry_price - tp_price) / risk, "bars_checked": checked}
            return {"outcome": "LOSS", "exit_time": bar["time"], "exit_price": sl_price, "realized_r": -1.0, "bars_checked": checked}
        if hit_sl:
            return {"outcome": "LOSS", "exit_time": bar["time"], "exit_price": sl_price, "realized_r": -1.0, "bars_checked": checked}
        if hit_tp:
            return {"outcome": "WIN", "exit_time": bar["time"], "exit_price": tp_price, "realized_r": (entry_price - tp_price) / risk, "bars_checked": checked}

    last = path.sort_values("time", kind="mergesort").iloc[-1]
    exit_price = safe_float(last["close"])
    return {"outcome": "TIMEOUT", "exit_time": last["time"], "exit_price": exit_price, "realized_r": (entry_price - exit_price) / risk, "bars_checked": checked}


def evaluate_trades(signals: pd.DataFrame, m1: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if signals.empty:
        return signals.copy()
    rows = []
    m1_sorted = m1.sort_values("time", kind="mergesort").reset_index(drop=True)
    last_m1_time = pd.Timestamp(m1_sorted["time"].max()) if not m1_sorted.empty else pd.NaT
    for _, row in signals.iterrows():
        entry_time = pd.Timestamp(row["entry_time"])
        full_horizon_available = bool(pd.notna(last_m1_time) and last_m1_time >= entry_time + pd.to_timedelta(float(args.horizon_hours), unit="h") - pd.to_timedelta(1, unit="m"))
        result = judge_sell_first_touch(
            m1_sorted,
            entry_time=entry_time,
            entry_price=safe_float(row["entry_price"]),
            sl_price=safe_float(row["sl_price"]),
            tp_price=safe_float(row["tp_price"]),
            risk=safe_float(row["risk_price"]),
            horizon_hours=float(args.horizon_hours),
            inbar_priority=str(args.inbar_priority),
        )
        out = row.to_dict()
        out.update(result)
        out["full_horizon_available"] = full_horizon_available
        if not full_horizon_available and result["outcome"] == "TIMEOUT":
            out["outcome"] = "NO_FULL_M1_HORIZON"
            out["realized_r"] = np.nan
        rows.append(out)
    df = pd.DataFrame(rows).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    df["entry_month"] = pd.to_datetime(df["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    df["lot_weighted_r"] = pd.to_numeric(df["realized_r"], errors="coerce") * pd.to_numeric(df["lot_multiplier"], errors="coerce")
    return df


def profit_factor(r_values: pd.Series) -> float:
    r = pd.to_numeric(r_values, errors="coerce").dropna()
    if r.empty:
        return np.nan
    gp = float(r[r > 0].sum())
    gl = float(-r[r < 0].sum())
    if gl == 0:
        return float("inf") if gp > 0 else np.nan
    return gp / gl


def max_drawdown_r(r_values: pd.Series) -> float:
    r = pd.to_numeric(r_values, errors="coerce").dropna()
    if r.empty:
        return 0.0
    eq = r.cumsum()
    peak = eq.cummax()
    return float((peak - eq).max())


def summarize_group(df: pd.DataFrame, *, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=group_cols + ["trades", "wins", "losses", "timeouts", "win_rate", "total_r", "lot_weighted_r", "avg_r", "pf", "max_dd_r", "first_entry_time", "last_entry_time"])
    eval_df = df[df["outcome"].isin(["WIN", "LOSS", "TIMEOUT"])].copy()
    rows = []
    if eval_df.empty:
        return pd.DataFrame(columns=group_cols + ["trades", "wins", "losses", "timeouts", "win_rate", "total_r", "lot_weighted_r", "avg_r", "pf", "max_dd_r", "first_entry_time", "last_entry_time"])
    grouped = eval_df.groupby(group_cols, dropna=False) if group_cols else [((), eval_df)]
    for key, g in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        r = pd.to_numeric(g["realized_r"], errors="coerce")
        row = {col: val for col, val in zip(group_cols, key)}
        row.update(
            {
                "trades": int(len(g)),
                "wins": int((g["outcome"] == "WIN").sum()),
                "losses": int((g["outcome"] == "LOSS").sum()),
                "timeouts": int((g["outcome"] == "TIMEOUT").sum()),
                "win_rate": float((g["outcome"] == "WIN").mean()),
                "total_r": float(r.sum()),
                "lot_weighted_r": float(pd.to_numeric(g["lot_weighted_r"], errors="coerce").sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "first_entry_time": g["entry_time"].min(),
                "last_entry_time": g["entry_time"].max(),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols, kind="mergesort").reset_index(drop=True) if group_cols else pd.DataFrame(rows)


def build_overall_lot_weighted_summary(trades: pd.DataFrame) -> pd.DataFrame:
    eval_df = trades[trades["outcome"].isin(["WIN", "LOSS", "TIMEOUT"])].copy()
    if eval_df.empty:
        return pd.DataFrame([{"condition_family_id": CONDITION_FAMILY_ID, "trades": 0}])
    r = pd.to_numeric(eval_df["realized_r"], errors="coerce")
    wr = pd.to_numeric(eval_df["lot_weighted_r"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "condition_family_id": CONDITION_FAMILY_ID,
                "trades": int(len(eval_df)),
                "wins": int((eval_df["outcome"] == "WIN").sum()),
                "losses": int((eval_df["outcome"] == "LOSS").sum()),
                "timeouts": int((eval_df["outcome"] == "TIMEOUT").sum()),
                "win_rate_unweighted": float((eval_df["outcome"] == "WIN").mean()),
                "total_r_unweighted": float(r.sum()),
                "total_r_lot_weighted": float(wr.sum()),
                "pf_unweighted": profit_factor(r),
                "pf_lot_weighted": profit_factor(wr),
                "max_dd_r_unweighted": max_drawdown_r(r),
                "max_dd_r_lot_weighted": max_drawdown_r(wr),
                "core_trades": int((eval_df["rank"] == "CORE_AB_CONFIRM").sum()),
                "b_only_trades": int((eval_df["rank"] == "B_ONLY_SAFE").sum()),
                "first_entry_time": eval_df["entry_time"].min(),
                "last_entry_time": eval_df["entry_time"].max(),
            }
        ]
    )


def build_signal_key(row: pd.Series) -> str:
    return "|".join(
        [
            str(row.get("condition_id", "")),
            str(row.get("symbol", SYMBOL)),
            str(row.get("direction", DIRECTION)),
            str(row.get("rank", "")),
            str(row.get("entry_time", "")),
            str(row.get("m15_close_time", "")),
        ]
    )


def build_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "schema_version": "gold_h1h4_bear_ab_classifier_signal_v1",
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": str(row.get("condition_id", "")),
        "strategy_id": CONDITION_FAMILY_ID,
        "symbol": str(row.get("symbol", SYMBOL)),
        "direction": str(row.get("direction", DIRECTION)),
        "rank": str(row.get("rank", "")),
        "signal_group": str(row.get("signal_group", "")),
        "a_pass": bool(row.get("a_pass", False)),
        "b_pass": bool(row.get("b_pass", False)),
        "trade_enabled": bool(row.get("trade_enabled", False)),
        "lot": {
            "base_lot": safe_float(row.get("base_lot", 0.0), 0.0),
            "lot_multiplier": safe_float(row.get("lot_multiplier", 0.0), 0.0),
            "effective_lot": safe_float(row.get("effective_lot", 0.0), 0.0),
        },
        "entry": {
            "entry_type": "NEXT_M15_OPEN_BACKTEST_OR_MARKET_ON_LIVE_SCAN",
            "signal_time": str(row.get("signal_time", "")),
            "m15_close_time": str(row.get("m15_close_time", "")),
            "entry_time": str(row.get("entry_time", "")),
            "entry_price_reference": safe_float(row.get("entry_price", np.nan)),
        },
        "risk": {
            "sl_price": safe_float(row.get("sl_price", np.nan)),
            "tp_price": safe_float(row.get("tp_price", np.nan)),
            "risk_price": safe_float(row.get("risk_price", np.nan)),
            "reward_price": safe_float(row.get("reward_price", np.nan)),
            "rr": safe_float(row.get("rr", 2.0), 2.0),
            "max_hold_hours": safe_float(row.get("max_hold_hours", 12.0), 12.0),
            "exit_rule": "SELL TP/SL first-touch by M1; same M1 bar conflict uses SL priority",
        },
        "context": {
            "d1": {
                "close_time": str(row.get("d1_close_time", "")),
                "close": safe_float(row.get("d1_close", np.nan)),
                "ema20": safe_float(row.get("d1_ema20", np.nan)),
            },
            "h4": {
                "close_time": str(row.get("h4_close_time", "")),
                "close": safe_float(row.get("h4_close", np.nan)),
                "ema20": safe_float(row.get("h4_ema20", np.nan)),
                "ema50": safe_float(row.get("h4_ema50", np.nan)),
            },
            "h1": {
                "close_time": str(row.get("h1_close_time", "")),
                "close": safe_float(row.get("h1_close", np.nan)),
                "ema20": safe_float(row.get("h1_ema20", np.nan)),
                "ema50": safe_float(row.get("h1_ema50", np.nan)),
                "ema20_slope3": safe_float(row.get("h1_ema20_slope3", np.nan)),
                "dist_e20_atr_sell": safe_float(row.get("h1_dist_e20_atr_sell", np.nan)),
            },
            "m15": {
                "time": str(row.get("time", "")),
                "close_time": str(row.get("m15_close_time", "")),
                "open": safe_float(row.get("open", np.nan)),
                "high": safe_float(row.get("high", np.nan)),
                "low": safe_float(row.get("low", np.nan)),
                "close": safe_float(row.get("close", np.nan)),
                "ema20": safe_float(row.get("ema20", np.nan)),
                "atr14": safe_float(row.get("atr14", np.nan)),
                "close_pos": safe_float(row.get("close_pos", np.nan)),
                "range_atr_ratio": safe_float(row.get("range_atr_ratio", np.nan)),
                "macd_hist": safe_float(row.get("macd_hist", np.nan)),
                "macd_hist_delta": safe_float(row.get("macd_hist_delta", np.nan)),
                "prev_low16": safe_float(row.get("m15_prev_low16", np.nan)),
                "prev_low6": safe_float(row.get("m15_prev_low6", np.nan)),
            },
        },
    }


def build_notification_text(payload: dict[str, Any]) -> str:
    lot = payload["lot"]
    entry = payload["entry"]
    risk = payload["risk"]
    ctx = payload["context"]
    emoji = "🔥" if payload["rank"] == "CORE_AB_CONFIRM" else "⚠️"
    return "\n".join(
        [
            "━━━━━━━━━━━━━━━━━━━━",
            f"{emoji} GOLD {payload['direction']} {payload['rank']}",
            f"condition: {payload['condition_id']}",
            f"A: {'PASS' if payload['a_pass'] else 'FAIL'} / B: {'PASS' if payload['b_pass'] else 'FAIL'}",
            f"trade_enabled: {payload['trade_enabled']}",
            f"lot: base={lot['base_lot']:.2f} x{lot['lot_multiplier']:.2f} => effective={lot['effective_lot']:.2f}",
            "",
            f"signal_time: {entry['signal_time']}",
            f"entry_time: {entry['entry_time']}",
            f"Entry ref: {entry['entry_price_reference']:.2f}",
            f"SL: {risk['sl_price']:.2f}",
            f"TP: {risk['tp_price']:.2f}",
            f"RR: {risk['rr']:.2f}",
            f"Max hold: {risk['max_hold_hours']:.1f}h",
            "",
            f"D1: close={ctx['d1']['close']:.2f} ema20={ctx['d1']['ema20']:.2f} close_time={ctx['d1']['close_time']}",
            f"H4: close={ctx['h4']['close']:.2f} ema20={ctx['h4']['ema20']:.2f} ema50={ctx['h4']['ema50']:.2f} close_time={ctx['h4']['close_time']}",
            f"H1: close={ctx['h1']['close']:.2f} ema20={ctx['h1']['ema20']:.2f} ema50={ctx['h1']['ema50']:.2f} distE20ATR={ctx['h1']['dist_e20_atr_sell']:.3f}",
            f"M15: close={ctx['m15']['close']:.2f} low={ctx['m15']['low']:.2f} close_pos={ctx['m15']['close_pos']:.3f} rangeATR={ctx['m15']['range_atr_ratio']:.3f}",
            f"M15 MACD hist={ctx['m15']['macd_hist']:.3f} delta={ctx['m15']['macd_hist_delta']:.3f}",
        ]
    )


def write_latest_preview(trades: pd.DataFrame, out_dir: Path) -> None:
    if trades.empty:
        (out_dir / "latest_signal_preview.json").write_text(json.dumps({"signal_found": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    latest = trades.sort_values("entry_time", kind="mergesort").iloc[-1]
    payload = build_payload(latest)
    intent = {
        "schema_version": "gold_h1h4_bear_ab_classifier_order_intent_v1",
        "dry_run": True,
        "intent_type": "OPEN_POSITION" if payload["trade_enabled"] else "OBSERVE_ONLY",
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": payload["condition_id"],
        "symbol": payload["symbol"],
        "direction": payload["direction"],
        "rank": payload["rank"],
        "trade_enabled": payload["trade_enabled"],
        "lot": payload["lot"],
        "entry_type": "MARKET_ON_SIGNAL",
        "signal_time": payload["entry"]["signal_time"],
        "entry_price_reference": payload["entry"]["entry_price_reference"],
        "sl_price": payload["risk"]["sl_price"],
        "tp_price": payload["risk"]["tp_price"],
        "rr": payload["risk"]["rr"],
        "max_hold_hours": payload["risk"]["max_hold_hours"],
        "source_signal": payload,
    }
    preview = {
        "signal_found": True,
        "payload": payload,
        "order_intent_dry_run": intent,
        "notification_preview": build_notification_text(payload),
    }
    (out_dir / "latest_signal_preview.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "notification_preview_latest.txt").write_text(preview["notification_preview"] + "\n", encoding="utf-8")
    (out_dir / "order_intent_dry_run_latest.json").write_text(json.dumps(intent, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_frames(args.csv_dir)
    write_csv(build_data_coverage(frames), args.out_dir / "data_coverage.csv")

    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m1 = frames["M1"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    m15_ctx = attach_context(m15, h1, h4, d1)
    raw = build_signal_candidates(m15_ctx, args)
    write_csv(raw, args.out_dir / "signals_all_raw.csv")
    write_csv(raw[raw["trade_enabled"]].copy(), args.out_dir / "signals_trade_enabled_raw.csv")

    cooldown = apply_common_cooldown(raw, int(args.cooldown_bars_m15))
    trades = evaluate_trades(cooldown, m1, args)
    write_csv(trades, args.out_dir / "trades_classified_cooldown.csv")

    eval_trades = trades[trades["outcome"].isin(["WIN", "LOSS", "TIMEOUT"])].copy()
    write_csv(summarize_group(eval_trades, group_cols=["rank", "condition_id"]), args.out_dir / "summary_by_rank.csv")
    write_csv(build_overall_lot_weighted_summary(eval_trades), args.out_dir / "summary_overall_lot_weighted.csv")
    write_csv(summarize_group(eval_trades, group_cols=["entry_month", "rank"]), args.out_dir / "monthly_by_rank.csv")

    target_start = pd.Timestamp(args.target_start)
    target_end = pd.Timestamp(args.target_end)
    target = eval_trades[(pd.to_datetime(eval_trades["entry_time"]) >= target_start) & (pd.to_datetime(eval_trades["entry_time"]) <= target_end)].copy()
    write_csv(target, args.out_dir / "target_window_20260428.csv")
    write_latest_preview(eval_trades, args.out_dir)

    print("[INFO] raw_signals=", len(raw))
    print("[INFO] trade_enabled_raw=", int(raw["trade_enabled"].sum()) if not raw.empty else 0)
    print("[INFO] cooldown_trades=", len(trades))
    if not eval_trades.empty:
        print("[INFO] summary_by_rank")
        print(summarize_group(eval_trades, group_cols=["rank", "condition_id"]).to_string(index=False))
        print("[INFO] overall_lot_weighted")
        print(build_overall_lot_weighted_summary(eval_trades).to_string(index=False))
        print("[INFO] target_window")
        cols = ["rank", "entry_time", "entry_price", "sl_price", "tp_price", "outcome", "realized_r", "lot_multiplier"]
        print(target[cols].to_string(index=False) if not target.empty else "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

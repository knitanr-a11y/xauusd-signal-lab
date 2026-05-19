#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run strict no-future backtest for the GOLD seven-candidate signal set.

Research-only script.

No Discord send.
No MT5 call.
No order_send.
No live/runtime ledger mutation.
No OpenAI call.

Important v2 fixes:
- M1 coverage is explicit. By default, post-cooldown signals before the first
  available M1 candle are dropped from trade evaluation instead of being counted
  as breakeven-like zero-R rows.
- Summary/monthly/portfolio stats use evaluated rows only.
- NO_M1_PATH rows can still be kept for diagnostics with
  --m1-coverage-policy keep_no_path, but they are never counted as wins/losses
  or breakevens in performance stats.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gold_strict_7_signal_specs import (  # noqa: E402
    DEFAULT_BROKER_SYMBOL,
    DEFAULT_SYMBOL,
    GOLD_PIP_SIZE,
    GoldStrictSignalSpec,
    get_signal_specs,
    validate_signal_specs,
)

SCHEMA_VERSION = "gold_strict_7_backtest_v2"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/gold_strict_7_signal_candidates")
EVALUATED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}
NON_EVALUATED_OUTCOMES = {"NO_M1_PATH", "NO_PATH", "INVALID_RISK"}

TIMEFRAME_MINUTES = {
    "M1": 1,
    "M5": 5,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

TRADE_COLUMNS = [
    "created_at_utc",
    "schema_version",
    "signal_id",
    "trade_id",
    "strategy_id",
    "candidate_family",
    "direction",
    "session",
    "broker_symbol",
    "symbol",
    "trigger_timeframe",
    "outcome_timeframe",
    "m1_coverage_status",
    "signal_time",
    "entry_time",
    "entry_price",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "tp_pips",
    "sl_pips",
    "rr",
    "spread_points_raw",
    "spread_pips_est",
    "spread_price_est",
    "outcome",
    "close_reason",
    "close_time",
    "close_price",
    "profit_pips_gross",
    "profit_pips_net",
    "profit_price_gross",
    "profit_price_net",
    "profit_r",
    "net_profit_r",
    "gross_profit_r",
    "mfe_pips",
    "mae_pips",
    "mfe_r",
    "mae_r",
    "holding_minutes",
    "bars_checked_m1",
    "same_bar_conflict",
    "cooldown_minutes",
    "cooldown_bars_m5",
    "strict_no_future_ok",
    "context_h1_close_time",
    "context_h4_close_time",
    "context_d1_close_time",
    "trigger_close_pos",
    "trigger_range_atr",
    "trigger_rsi14",
    "trigger_stoch_k",
    "trigger_stoch_d",
    "trigger_cci20",
    "trigger_bb_pos",
    "trigger_kc_pos",
    "reason",
]

SUMMARY_COLUMNS = [
    "strategy_id",
    "candidate_family",
    "direction",
    "session",
    "signal_count",
    "evaluated_trade_count",
    "trade_count",
    "no_m1_path_count",
    "win_count",
    "loss_count",
    "breakeven_count",
    "win_rate",
    "total_r",
    "avg_r",
    "profit_factor",
    "max_drawdown_r",
    "max_losing_streak",
    "avg_holding_minutes",
    "median_holding_minutes",
    "first_entry_time",
    "last_entry_time",
    "months_with_trades",
    "strict_no_future_all_ok",
]

MONTHLY_COLUMNS = [
    "strategy_id",
    "candidate_family",
    "direction",
    "session",
    "entry_month",
    "signal_count",
    "evaluated_trade_count",
    "trade_count",
    "no_m1_path_count",
    "win_count",
    "loss_count",
    "breakeven_count",
    "win_rate",
    "total_r",
    "avg_r",
    "profit_factor",
    "max_drawdown_r",
]

OVERLAP_COLUMNS = [
    "entry_time",
    "signals_at_same_time",
    "buy_count",
    "sell_count",
    "strategy_ids",
    "directions",
    "total_r_same_time",
]


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def ensure_parent_dir(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent_dir(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_text(path: str | Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def clean_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return clean_str(value)
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def id_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "UNKNOWN_TIME"
    return pd.Timestamp(ts).strftime("%Y%m%d_%H%M")


def read_ohlc_csv(path: str | Path, *, tail_bars: int = 0) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    df = pd.read_csv(windows_long_path(p), sep=sniff_sep(p), encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"datetime": "time", "date": "time", "timestamp": "time", "tickvolume": "tick_volume", "tick volume": "tick_volume", "volume": "tick_volume"})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing columns in {p}: {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required).sort_values("time", kind="mergesort").drop_duplicates("time", keep="last").reset_index(drop=True)
    if int(tail_bars) > 0 and len(df) > int(tail_bars):
        df = df.tail(int(tail_bars)).reset_index(drop=True)
    return df


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.astype(float).ewm(span=int(span), adjust=False, min_periods=int(span)).mean()


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]).abs(), (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(int(period), min_periods=int(period)).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.astype(float).diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def stoch_kd(df: pd.DataFrame, k_period: int = 20, d_period: int = 3) -> tuple[pd.Series, pd.Series]:
    low_min = df["low"].rolling(k_period, min_periods=k_period).min()
    high_max = df["high"].rolling(k_period, min_periods=k_period).max()
    k = 100.0 * (df["close"] - low_min) / (high_max - low_min).replace(0.0, np.nan)
    d = k.rolling(d_period, min_periods=d_period).mean()
    return k, d


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    ma = tp.rolling(period, min_periods=period).mean()
    mad = (tp - ma).abs().rolling(period, min_periods=period).mean()
    return (tp - ma) / (0.015 * mad.replace(0.0, np.nan))


def add_indicators(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["close_time"] = out["time"] + pd.to_timedelta(TIMEFRAME_MINUTES[tf], unit="m")
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out["atr14"] = atr(out, 14)
    out["atr50"] = atr(out, 50)
    macd = ema(out["close"], 6) - ema(out["close"], 13)
    sig = ema(macd, 4)
    out["macd"] = macd
    out["macd_signal"] = sig
    out["macd_hist"] = macd - sig
    out["macd_hist_delta"] = out["macd_hist"] - out["macd_hist"].shift(1)
    out["rsi14"] = rsi(out["close"], 14)
    out["stoch_k20"], out["stoch_d3"] = stoch_kd(out, 20, 3)
    out["cci20"] = cci(out, 20)
    out["range"] = out["high"] - out["low"]
    out["close_pos"] = np.where(out["range"] > 0, (out["close"] - out["low"]) / out["range"], np.nan)
    out["upper_wick_ratio"] = np.where(out["range"] > 0, (out["high"] - out[["open", "close"]].max(axis=1)) / out["range"], np.nan)
    out["lower_wick_ratio"] = np.where(out["range"] > 0, (out[["open", "close"]].min(axis=1) - out["low"]) / out["range"], np.nan)
    out["range_atr"] = out["range"] / out["atr14"].replace(0.0, np.nan)
    out["ema20_slope3"] = out["ema20"] - out["ema20"].shift(3)
    out["ema50_slope3"] = out["ema50"] - out["ema50"].shift(3)

    bb_mid = out["close"].rolling(20, min_periods=20).mean()
    bb_std = out["close"].rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid20"] = bb_mid
    out["bb_upper20"] = bb_mid + 2.0 * bb_std
    out["bb_lower20"] = bb_mid - 2.0 * bb_std
    out["bb_pos20"] = (out["close"] - out["bb_lower20"]) / (out["bb_upper20"] - out["bb_lower20"]).replace(0.0, np.nan)

    kc_mid = out["ema20"]
    kc_atr = out["atr14"]
    out["kc_upper20_1p5"] = kc_mid + 1.5 * kc_atr
    out["kc_lower20_1p5"] = kc_mid - 1.5 * kc_atr
    out["kc_pos20_1p5"] = (out["close"] - out["kc_lower20_1p5"]) / (out["kc_upper20_1p5"] - out["kc_lower20_1p5"]).replace(0.0, np.nan)

    vol = out["tick_volume"] if "tick_volume" in out.columns else pd.Series(1.0, index=out.index)
    out["vwap96"] = (out["close"] * vol).rolling(96, min_periods=20).sum() / vol.rolling(96, min_periods=20).sum().replace(0.0, np.nan)

    for window in [6, 12, 24, 48, 96]:
        out[f"prev_low_{window}"] = out["low"].shift(1).rolling(window, min_periods=window).min()
        out[f"prev_high_{window}"] = out["high"].shift(1).rolling(window, min_periods=window).max()
    return out


def prefix_context(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    cols = ["close_time", "open", "high", "low", "close", "ema20", "ema50", "ema200", "atr14", "atr50", "macd", "macd_signal", "macd_hist", "macd_hist_delta", "rsi14", "stoch_k20", "stoch_d3", "cci20", "range", "close_pos", "range_atr", "ema20_slope3", "ema50_slope3", "prev_low_6", "prev_low_12", "prev_low_24", "prev_low_48", "prev_low_96", "prev_high_6", "prev_high_12", "prev_high_24", "prev_high_48", "prev_high_96"]
    use = [c for c in cols if c in df.columns]
    out = df[use].copy().sort_values("close_time", kind="mergesort")
    rename = {"close_time": f"{prefix}_close_time"}
    rename.update({c: f"{prefix}_{c}" for c in use if c != "close_time"})
    return out.rename(columns=rename)


def attach_strict_context(m5: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    base = m5.copy().sort_values("close_time", kind="mergesort").reset_index(drop=True)
    out = pd.merge_asof(base, prefix_context(h1, "h1"), left_on="close_time", right_on="h1_close_time", direction="backward")
    out = pd.merge_asof(out, prefix_context(h4, "h4"), left_on="close_time", right_on="h4_close_time", direction="backward")
    out = pd.merge_asof(out, prefix_context(d1, "d1"), left_on="close_time", right_on="d1_close_time", direction="backward")
    out["strict_no_future_ok"] = ((pd.to_datetime(out["h1_close_time"], errors="coerce") <= pd.to_datetime(out["close_time"], errors="coerce")) & (pd.to_datetime(out["h4_close_time"], errors="coerce") <= pd.to_datetime(out["close_time"], errors="coerce")) & (pd.to_datetime(out["d1_close_time"], errors="coerce") <= pd.to_datetime(out["close_time"], errors="coerce"))).fillna(False)
    return out


def session_mask(df: pd.DataFrame, session: str) -> pd.Series:
    hour = pd.to_datetime(df["close_time"], errors="coerce").dt.hour
    if session == "ALL":
        return pd.Series(True, index=df.index)
    if session == "LONDON":
        return hour.between(8, 16, inclusive="both")
    if session == "NY":
        return hour.between(13, 22, inclusive="both")
    if session == "LONDON_NY":
        return hour.between(8, 22, inclusive="both")
    raise ValueError(f"unsupported session: {session}")


def h1_down_context(df: pd.DataFrame) -> pd.Series:
    return (df["h1_close"] < df["h1_ema20"]) & (df["h1_ema20"] < df["h1_ema50"])


def h4_down_context(df: pd.DataFrame) -> pd.Series:
    return df["h4_ema20"] < df["h4_ema50"]


def d1_down_context(df: pd.DataFrame) -> pd.Series:
    return df["d1_close"] < df["d1_ema20"]


def detect_spec_candidates(ctx: pd.DataFrame, spec: GoldStrictSignalSpec) -> pd.DataFrame:
    base = ctx.copy()
    sm = session_mask(base, spec.session)
    strict = base["strict_no_future_ok"].astype(bool)

    if spec.family == "KC_CCI150":
        mask = strict & sm & (base["cci20"] >= float(spec.cci_threshold)) & (base["high"] >= base["kc_upper20_1p5"]) & (base["close"] < base["open"]) & (base["upper_wick_ratio"] >= float(spec.rejection_threshold)) & (base["close_pos"] <= 0.45)
        reason = "SELL KC upper rejection with CCI >= 150, bearish M5 close, London session."
    elif spec.family == "SWEEP_RECLAIM_RSI":
        mask = strict & sm & (base["low"] < base["prev_low_24"]) & (base["close"] > base["prev_low_24"]) & (base["rsi14"] <= float(spec.rsi_threshold)) & (base["lower_wick_ratio"] >= float(spec.rejection_threshold)) & (base["close_pos"] >= 0.50)
        reason = "BUY sweep below previous low then reclaim, RSI low, lower-wick rejection."
    elif spec.family == "STOCH_BB_KTURN":
        mask = strict & sm & (base["low"] <= base["bb_lower20"]) & (base["stoch_k20"] <= 35.0) & (base["stoch_k20"] > base["stoch_d3"]) & (base["lower_wick_ratio"] >= float(spec.rejection_threshold)) & (base["close_pos"] >= 0.45)
        reason = "BUY BB lower-band rejection with Stoch K > D turn-up filter."
    elif spec.family == "DONCHIAN_MACD_RANGE":
        lb = int(spec.donchian_lookback)
        if lb <= 0:
            raise ValueError(f"{spec.strategy_id}: donchian_lookback must be positive")
        mask = strict & sm & h1_down_context(base) & h4_down_context(base) & d1_down_context(base) & (base["low"] < base[f"prev_low_{lb}"]) & (base["macd_hist"] < 0) & (base["macd_hist_delta"] < 0) & (base["range_atr"] >= float(spec.min_range_atr)) & (base["close_pos"] <= 0.50)
        reason = f"SELL H1/H4/D1 bearish context, Donchian{lb} low break, MACD negative, range >= {spec.min_range_atr} ATR."
    elif spec.family == "BB_RSI_REJECTION":
        mask = strict & sm & (base["low"] <= base["bb_lower20"]) & (base["rsi14"] <= float(spec.rsi_threshold)) & (base["lower_wick_ratio"] >= float(spec.rejection_threshold)) & (base["close_pos"] >= 0.50)
        reason = "BUY BB lower-band touch, RSI30 zone, lower-wick rejection."
    else:
        raise ValueError(f"unsupported family: {spec.family}")

    rows = base[mask.fillna(False)].copy()
    if rows.empty:
        return pd.DataFrame()
    rows["strategy_id"] = spec.strategy_id
    rows["candidate_family"] = spec.family
    rows["direction"] = spec.direction
    rows["session"] = spec.session
    rows["tp_pips"] = float(spec.tp_pips)
    rows["sl_pips"] = float(spec.sl_pips)
    rows["rr"] = float(spec.rr)
    rows["cooldown_minutes"] = int(spec.cooldown_minutes)
    rows["cooldown_bars_m5"] = int(spec.cooldown_bars_m5)
    rows["reason"] = reason
    return rows.sort_values("close_time", kind="mergesort").reset_index(drop=True)


def apply_cooldown(candidates: pd.DataFrame, spec: GoldStrictSignalSpec) -> pd.DataFrame:
    if candidates.empty or spec.cooldown_bars_m5 <= 0:
        return candidates.copy()
    cooldown = pd.to_timedelta(int(spec.cooldown_minutes), unit="m")
    accepted: list[dict[str, Any]] = []
    last_time: pd.Timestamp | None = None
    for _, row in candidates.sort_values("close_time", kind="mergesort").iterrows():
        t = pd.Timestamp(row["close_time"])
        if last_time is None or t >= last_time + cooldown:
            accepted.append(row.to_dict())
            last_time = t
    return pd.DataFrame(accepted).reset_index(drop=True) if accepted else pd.DataFrame(columns=candidates.columns)


def no_m1_path_row(row: pd.Series, spec: GoldStrictSignalSpec, *, broker_symbol: str, coverage_status: str) -> dict[str, Any]:
    entry_time = pd.Timestamp(row["close_time"])
    entry_price = float(row["close"])
    sl = entry_price - spec.sl_price_distance if spec.direction == "BUY" else entry_price + spec.sl_price_distance
    tp = entry_price + spec.tp_price_distance if spec.direction == "BUY" else entry_price - spec.tp_price_distance
    signal_id = f"{spec.strategy_id}|{spec.direction}|{id_time_text(entry_time)}"
    return {col: "" for col in TRADE_COLUMNS} | {
        "created_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "signal_id": signal_id,
        "trade_id": f"GOLD_STRICT7_{spec.strategy_id}_{id_time_text(entry_time)}",
        "strategy_id": spec.strategy_id,
        "candidate_family": spec.family,
        "direction": spec.direction,
        "session": spec.session,
        "broker_symbol": broker_symbol,
        "symbol": DEFAULT_SYMBOL,
        "trigger_timeframe": spec.trigger_timeframe,
        "outcome_timeframe": spec.outcome_timeframe,
        "m1_coverage_status": coverage_status,
        "signal_time": time_text(entry_time),
        "entry_time": time_text(entry_time),
        "entry_price": round(entry_price, 5),
        "entry_price_reference": round(entry_price, 5),
        "sl_price": round(sl, 5),
        "tp_price": round(tp, 5),
        "tp_pips": float(spec.tp_pips),
        "sl_pips": float(spec.sl_pips),
        "rr": float(spec.rr),
        "outcome": "NO_M1_PATH",
        "close_reason": "NO_M1_PATH",
        "strict_no_future_ok": bool(row.get("strict_no_future_ok", False)),
        "context_h1_close_time": time_text(row.get("h1_close_time")),
        "context_h4_close_time": time_text(row.get("h4_close_time")),
        "context_d1_close_time": time_text(row.get("d1_close_time")),
        "reason": clean_str(row.get("reason")),
    }


def evaluate_one_candidate(row: pd.Series, m1: pd.DataFrame, spec: GoldStrictSignalSpec, *, broker_symbol: str, inbar_priority: str) -> dict[str, Any]:
    direction = spec.direction
    entry_time = pd.Timestamp(row["close_time"])
    entry_price = float(row["close"])
    sl_dist = spec.sl_price_distance
    tp_dist = spec.tp_price_distance
    sl_price = entry_price - sl_dist if direction == "BUY" else entry_price + sl_dist
    tp_price = entry_price + tp_dist if direction == "BUY" else entry_price - tp_dist
    path = m1[(m1["time"] > entry_time) & (m1["time"] <= entry_time + pd.Timedelta(hours=24))].copy()
    if path.empty:
        return no_m1_path_row(row, spec, broker_symbol=broker_symbol, coverage_status="NO_M1_AFTER_ENTRY_WITHIN_24H")

    spread_raw = clean_float(row.get("spread"), 0.0) or 0.0
    spread_pips = float(spread_raw) / 10.0
    spread_price = spread_pips * GOLD_PIP_SIZE

    if direction == "BUY":
        favorable = path["high"] - entry_price
        adverse = path["low"] - entry_price
        tp_hit = path["high"] >= tp_price
        sl_hit = path["low"] <= sl_price
    else:
        favorable = entry_price - path["low"]
        adverse = entry_price - path["high"]
        tp_hit = path["low"] <= tp_price
        sl_hit = path["high"] >= sl_price

    mfe_pips = float(favorable.max() / GOLD_PIP_SIZE)
    mae_pips = float(adverse.min() / GOLD_PIP_SIZE)
    hit = (tp_hit | sl_hit).to_numpy(dtype=bool)
    same_bar_conflict = False
    if hit.any():
        k = int(np.argmax(hit))
        hit_row = path.iloc[k]
        both = bool(tp_hit.iloc[k] and sl_hit.iloc[k])
        same_bar_conflict = both
        if both:
            close_reason = "SL" if inbar_priority.upper() == "SL" else "TP"
        elif bool(sl_hit.iloc[k]):
            close_reason = "SL"
        else:
            close_reason = "TP"
        close_time = time_text(hit_row["time"])
        close_price = sl_price if close_reason == "SL" else tp_price
        outcome = "LOSS" if close_reason == "SL" else "WIN"
    else:
        last = path.iloc[-1]
        close_reason = "TIMEOUT_24H_CLOSE"
        close_time = time_text(last["time"])
        close_price = float(last["close"])
        gross_price_tmp = close_price - entry_price if direction == "BUY" else entry_price - close_price
        net_price_tmp = gross_price_tmp - spread_price
        outcome = "WIN" if net_price_tmp > 0 else ("LOSS" if net_price_tmp < 0 else "BREAKEVEN")

    gross_price = close_price - entry_price if direction == "BUY" else entry_price - close_price
    net_price = gross_price - spread_price
    gross_r = gross_price / sl_dist if sl_dist > 0 else None
    net_r = net_price / sl_dist if sl_dist > 0 else None
    holding_minutes = (pd.Timestamp(close_time) - entry_time).total_seconds() / 60.0
    signal_id = f"{spec.strategy_id}|{direction}|{id_time_text(entry_time)}"

    return {
        "created_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "signal_id": signal_id,
        "trade_id": f"GOLD_STRICT7_{spec.strategy_id}_{id_time_text(entry_time)}",
        "strategy_id": spec.strategy_id,
        "candidate_family": spec.family,
        "direction": direction,
        "session": spec.session,
        "broker_symbol": broker_symbol,
        "symbol": DEFAULT_SYMBOL,
        "trigger_timeframe": spec.trigger_timeframe,
        "outcome_timeframe": spec.outcome_timeframe,
        "m1_coverage_status": "EVALUATED",
        "signal_time": time_text(entry_time),
        "entry_time": time_text(entry_time),
        "entry_price": round(entry_price, 5),
        "entry_price_reference": round(entry_price, 5),
        "sl_price": round(sl_price, 5),
        "tp_price": round(tp_price, 5),
        "tp_pips": float(spec.tp_pips),
        "sl_pips": float(spec.sl_pips),
        "rr": float(spec.rr),
        "spread_points_raw": spread_raw,
        "spread_pips_est": spread_pips,
        "spread_price_est": spread_price,
        "outcome": outcome,
        "close_reason": close_reason,
        "close_time": close_time,
        "close_price": round(close_price, 5),
        "profit_pips_gross": gross_price / GOLD_PIP_SIZE,
        "profit_pips_net": net_price / GOLD_PIP_SIZE,
        "profit_price_gross": gross_price,
        "profit_price_net": net_price,
        "profit_r": net_r,
        "net_profit_r": net_r,
        "gross_profit_r": gross_r,
        "mfe_pips": mfe_pips,
        "mae_pips": mae_pips,
        "mfe_r": mfe_pips / float(spec.sl_pips),
        "mae_r": mae_pips / float(spec.sl_pips),
        "holding_minutes": holding_minutes,
        "bars_checked_m1": int(len(path)),
        "same_bar_conflict": same_bar_conflict,
        "cooldown_minutes": int(spec.cooldown_minutes),
        "cooldown_bars_m5": int(spec.cooldown_bars_m5),
        "strict_no_future_ok": bool(row.get("strict_no_future_ok", False)),
        "context_h1_close_time": time_text(row.get("h1_close_time")),
        "context_h4_close_time": time_text(row.get("h4_close_time")),
        "context_d1_close_time": time_text(row.get("d1_close_time")),
        "trigger_close_pos": clean_float(row.get("close_pos")),
        "trigger_range_atr": clean_float(row.get("range_atr")),
        "trigger_rsi14": clean_float(row.get("rsi14")),
        "trigger_stoch_k": clean_float(row.get("stoch_k20")),
        "trigger_stoch_d": clean_float(row.get("stoch_d3")),
        "trigger_cci20": clean_float(row.get("cci20")),
        "trigger_bb_pos": clean_float(row.get("bb_pos20")),
        "trigger_kc_pos": clean_float(row.get("kc_pos20_1p5")),
        "reason": clean_str(row.get("reason")),
    }


def evaluate_candidates(candidates_by_spec: dict[str, pd.DataFrame], specs: list[GoldStrictSignalSpec], m1: pd.DataFrame, *, broker_symbol: str, inbar_priority: str, m1_coverage_policy: str) -> tuple[pd.DataFrame, dict[str, int], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    dropped_before_m1: dict[str, int] = {}
    post_cooldown_counts: dict[str, int] = {}
    spec_by_id = {s.strategy_id: s for s in specs}
    m1_first = pd.Timestamp(m1["time"].min()) if not m1.empty else None
    for strategy_id, candidates in candidates_by_spec.items():
        spec = spec_by_id[strategy_id]
        cooled = apply_cooldown(candidates, spec)
        post_cooldown_counts[strategy_id] = int(len(cooled))
        if m1_first is not None:
            before_mask = pd.to_datetime(cooled["close_time"], errors="coerce") < m1_first if not cooled.empty else pd.Series([], dtype=bool)
            dropped_before_m1[strategy_id] = int(before_mask.sum())
            if m1_coverage_policy == "drop" and not cooled.empty:
                cooled = cooled[~before_mask].copy()
        else:
            dropped_before_m1[strategy_id] = int(len(cooled))
            if m1_coverage_policy == "drop":
                cooled = cooled.iloc[0:0].copy()
        for _, row in cooled.iterrows():
            if m1_first is not None and pd.Timestamp(row["close_time"]) < m1_first and m1_coverage_policy == "keep_no_path":
                rows.append(no_m1_path_row(row, spec, broker_symbol=broker_symbol, coverage_status="BEFORE_FIRST_M1"))
            else:
                rows.append(evaluate_one_candidate(row, m1, spec, broker_symbol=broker_symbol, inbar_priority=inbar_priority))
    if not rows:
        return pd.DataFrame(columns=TRADE_COLUMNS), dropped_before_m1, post_cooldown_counts
    return pd.DataFrame(rows, columns=TRADE_COLUMNS).sort_values(["entry_time", "strategy_id"], kind="mergesort").reset_index(drop=True), dropped_before_m1, post_cooldown_counts


def evaluated_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "outcome" not in df.columns:
        return df.iloc[0:0].copy()
    return df[df["outcome"].astype(str).str.upper().isin(EVALUATED_OUTCOMES)].copy()


def profit_factor(r: pd.Series) -> float | None:
    vals = pd.to_numeric(r, errors="coerce").dropna()
    if vals.empty:
        return None
    pos = float(vals[vals > 0].sum())
    neg = float(-vals[vals < 0].sum())
    if neg <= 1e-12:
        return float("inf") if pos > 0 else None
    return pos / neg


def max_drawdown_r(r: pd.Series) -> float:
    vals = pd.to_numeric(r, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    if len(vals) == 0:
        return 0.0
    equity = np.cumsum(vals)
    peak = np.maximum.accumulate(equity)
    return float((equity - peak).min())


def max_losing_streak(outcomes: pd.Series) -> int:
    max_streak = 0
    cur = 0
    for item in outcomes.astype(str).str.upper().tolist():
        if item == "LOSS":
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 0
    return int(max_streak)


def summarize_group(group_all: pd.DataFrame) -> dict[str, Any]:
    group = evaluated_only(group_all)
    r = pd.to_numeric(group["profit_r"], errors="coerce").fillna(0.0)
    outcomes = group["outcome"].astype(str).str.upper() if not group.empty else pd.Series([], dtype=str)
    entry_times = pd.to_datetime(group["entry_time"], errors="coerce") if not group.empty else pd.Series([], dtype="datetime64[ns]")
    holding = pd.to_numeric(group["holding_minutes"], errors="coerce") if not group.empty else pd.Series([], dtype=float)
    win_count = int((r > 0).sum())
    loss_count = int((r < 0).sum())
    breakeven_count = int((r == 0).sum())
    no_m1_path_count = int(group_all["outcome"].astype(str).str.upper().eq("NO_M1_PATH").sum()) if not group_all.empty and "outcome" in group_all.columns else 0
    return {
        "signal_count": int(len(group_all)),
        "evaluated_trade_count": int(len(group)),
        "trade_count": int(len(group)),
        "no_m1_path_count": no_m1_path_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "breakeven_count": breakeven_count,
        "win_rate": None if len(group) == 0 else win_count / len(group),
        "total_r": float(r.sum()) if len(group) else 0.0,
        "avg_r": None if len(group) == 0 else float(r.mean()),
        "profit_factor": profit_factor(r),
        "max_drawdown_r": max_drawdown_r(r),
        "max_losing_streak": max_losing_streak(outcomes),
        "avg_holding_minutes": None if holding.dropna().empty else float(holding.mean()),
        "median_holding_minutes": None if holding.dropna().empty else float(holding.median()),
        "first_entry_time": time_text(entry_times.min()) if not entry_times.dropna().empty else "",
        "last_entry_time": time_text(entry_times.max()) if not entry_times.dropna().empty else "",
        "months_with_trades": int(entry_times.dt.strftime("%Y-%m").nunique()) if not entry_times.dropna().empty else 0,
    }


def build_summary(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    rows: list[dict[str, Any]] = []
    for (strategy_id, family, direction, session), group in trades.groupby(["strategy_id", "candidate_family", "direction", "session"], dropna=False):
        rows.append({"strategy_id": strategy_id, "candidate_family": family, "direction": direction, "session": session, **summarize_group(group), "strict_no_future_all_ok": bool(group["strict_no_future_ok"].astype(bool).all())})
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS).sort_values("strategy_id", kind="mergesort").reset_index(drop=True)


def build_monthly(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=MONTHLY_COLUMNS)
    work = trades.copy()
    work["entry_month"] = pd.to_datetime(work["entry_time"], errors="coerce").dt.strftime("%Y-%m")
    rows: list[dict[str, Any]] = []
    for (strategy_id, family, direction, session, month), group in work.groupby(["strategy_id", "candidate_family", "direction", "session", "entry_month"], dropna=False):
        stats = summarize_group(group)
        rows.append({"strategy_id": strategy_id, "candidate_family": family, "direction": direction, "session": session, "entry_month": month, **{k: stats[k] for k in ["signal_count", "evaluated_trade_count", "trade_count", "no_m1_path_count", "win_count", "loss_count", "breakeven_count", "win_rate", "total_r", "avg_r", "profit_factor", "max_drawdown_r"]}})
    return pd.DataFrame(rows, columns=MONTHLY_COLUMNS).sort_values(["strategy_id", "entry_month"], kind="mergesort").reset_index(drop=True)


def build_overlap(trades: pd.DataFrame) -> pd.DataFrame:
    eval_trades = evaluated_only(trades)
    if eval_trades.empty:
        return pd.DataFrame(columns=OVERLAP_COLUMNS)
    rows: list[dict[str, Any]] = []
    for entry_time, group in eval_trades.groupby("entry_time", dropna=False):
        if len(group) <= 1:
            continue
        rows.append({"entry_time": entry_time, "signals_at_same_time": int(len(group)), "buy_count": int(group["direction"].astype(str).eq("BUY").sum()), "sell_count": int(group["direction"].astype(str).eq("SELL").sum()), "strategy_ids": ";".join(group["strategy_id"].astype(str).tolist()), "directions": ";".join(sorted(set(group["direction"].astype(str)))), "total_r_same_time": float(pd.to_numeric(group["profit_r"], errors="coerce").fillna(0.0).sum())})
    return pd.DataFrame(rows, columns=OVERLAP_COLUMNS).sort_values("entry_time", kind="mergesort").reset_index(drop=True) if rows else pd.DataFrame(columns=OVERLAP_COLUMNS)


def resolve_csv_paths(args: argparse.Namespace) -> dict[str, Path]:
    csv_dir = Path(args.csv_dir)
    return {"M1": Path(args.gold_m1_csv) if args.gold_m1_csv else csv_dir / "goldsharp_m1.csv", "M5": Path(args.gold_m5_csv) if args.gold_m5_csv else csv_dir / "goldsharp_m5.csv", "H1": Path(args.gold_h1_csv) if args.gold_h1_csv else csv_dir / "goldsharp_h1.csv", "H4": Path(args.gold_h4_csv) if args.gold_h4_csv else csv_dir / "goldsharp_h4.csv", "D1": Path(args.gold_d1_csv) if args.gold_d1_csv else csv_dir / "goldsharp_d1.csv"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run strict no-future backtest for GOLD seven signal candidates.")
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--gold-m1-csv", default="")
    parser.add_argument("--gold-m5-csv", default="")
    parser.add_argument("--gold-h1-csv", default="")
    parser.add_argument("--gold-h4-csv", default="")
    parser.add_argument("--gold-d1-csv", default="")
    parser.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument("--m1-coverage-policy", choices=["drop", "keep_no_path"], default="drop", help="drop excludes post-cooldown signals before first M1 from trade stats; keep_no_path writes them as NO_M1_PATH diagnostics.")
    parser.add_argument("--tail-m1", type=int, default=0)
    parser.add_argument("--tail-m5", type=int, default=0)
    parser.add_argument("--tail-h1", type=int, default=0)
    parser.add_argument("--tail-h4", type=int, default=0)
    parser.add_argument("--tail-d1", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    specs = get_signal_specs()
    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    paths = resolve_csv_paths(args)

    print("=" * 80, flush=True)
    print("GOLD strict 7 signal backtest", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"m1_coverage_policy: {args.m1_coverage_policy}", flush=True)
    print(f"out_dir: {out_dir}", flush=True)
    for tf, path in paths.items():
        print(f"{tf}: {path}", flush=True)
    print("=" * 80, flush=True)

    raw = {"M1": read_ohlc_csv(paths["M1"], tail_bars=args.tail_m1), "M5": read_ohlc_csv(paths["M5"], tail_bars=args.tail_m5), "H1": read_ohlc_csv(paths["H1"], tail_bars=args.tail_h1), "H4": read_ohlc_csv(paths["H4"], tail_bars=args.tail_h4), "D1": read_ohlc_csv(paths["D1"], tail_bars=args.tail_d1)}
    frames = {tf: add_indicators(df, tf) for tf, df in raw.items()}
    ctx = attach_strict_context(frames["M5"], frames["H1"], frames["H4"], frames["D1"])

    candidates_by_spec: dict[str, pd.DataFrame] = {}
    candidate_rows: list[pd.DataFrame] = []
    for spec in specs:
        cand = detect_spec_candidates(ctx, spec)
        candidates_by_spec[spec.strategy_id] = cand
        if not cand.empty:
            candidate_rows.append(cand.assign(raw_candidate_count_before_cooldown=len(cand)))
        print(f"candidate {spec.strategy_id}: raw_rows={len(cand)}", flush=True)

    all_candidates = pd.concat(candidate_rows, ignore_index=True, sort=False) if candidate_rows else pd.DataFrame()
    trades, dropped_before_m1, post_cooldown_counts = evaluate_candidates(candidates_by_spec, specs, frames["M1"], broker_symbol=str(args.broker_symbol), inbar_priority=str(args.inbar_priority), m1_coverage_policy=str(args.m1_coverage_policy))
    summary = build_summary(trades)
    monthly = build_monthly(trades)
    overlap = build_overlap(trades)
    eval_trades = evaluated_only(trades)

    trades_path = out_dir / "gold_strict_7_candidates_trades.csv"
    candidates_path = out_dir / "gold_strict_7_candidates_raw.csv"
    summary_path = out_dir / "gold_strict_7_candidates_summary.csv"
    monthly_path = out_dir / "gold_strict_7_candidates_monthly.csv"
    overlap_path = out_dir / "gold_strict_7_candidates_overlap.csv"
    json_path = out_dir / "gold_strict_7_candidates_portfolio_summary.json"

    write_csv(all_candidates, candidates_path)
    write_csv(trades, trades_path)
    write_csv(summary, summary_path)
    write_csv(monthly, monthly_path)
    write_csv(overlap, overlap_path)

    portfolio_stats = summarize_group(trades) if not trades.empty else {}
    summary_json = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "script": "scripts/gold_strict_7_signals/run_gold_strict_7_backtest_from_csv.py",
        "m1_coverage_policy": str(args.m1_coverage_policy),
        "inputs": {tf: str(path) for tf, path in paths.items()},
        "outputs": {"raw_candidates_csv": str(candidates_path), "trades_csv": str(trades_path), "summary_csv": str(summary_path), "monthly_csv": str(monthly_path), "overlap_csv": str(overlap_path), "portfolio_summary_json": str(json_path)},
        "rows": {"m1": int(len(raw["M1"])), "m5": int(len(raw["M5"])), "h1": int(len(raw["H1"])), "h4": int(len(raw["H4"])), "d1": int(len(raw["D1"])), "strict_joined_m5": int(len(ctx)), "raw_candidates": int(len(all_candidates)), "post_cooldown_signals_before_m1_filter": int(sum(post_cooldown_counts.values())), "dropped_before_first_m1": int(sum(dropped_before_m1.values())), "trade_rows_written": int(len(trades)), "evaluated_trades": int(len(eval_trades)), "summary_rows": int(len(summary)), "monthly_rows": int(len(monthly)), "overlap_rows": int(len(overlap))},
        "candidate_raw_counts": {spec.strategy_id: int(len(candidates_by_spec.get(spec.strategy_id, []))) for spec in specs},
        "candidate_post_cooldown_counts": post_cooldown_counts,
        "candidate_dropped_before_first_m1_counts": dropped_before_m1,
        "candidate_trade_counts_evaluated": summary.set_index("strategy_id")["evaluated_trade_count"].to_dict() if not summary.empty else {},
        "portfolio_stats_all_evaluated_signals_no_overlap_filter": portfolio_stats,
        "no_future_contract": {"trigger_timeframe": "M5", "outcome_timeframe": "M1", "higher_timeframe_rule": "H1/H4/D1 context_close_time <= M5 close_time", "forming_higher_timeframe_allowed": False, "all_trades_strict_no_future_ok": bool(trades["strict_no_future_ok"].astype(bool).all()) if not trades.empty else True, "inbar_priority": str(args.inbar_priority)},
        "safety": {"discord_send": False, "mt5_calls": False, "order_send": False, "openai_calls": False, "runtime_state_mutation": False},
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(json_path, summary_json)

    print("=" * 80, flush=True)
    print(json.dumps({"cycle_ok": True, "schema_version": SCHEMA_VERSION, "m1_coverage_policy": str(args.m1_coverage_policy), "trade_rows_written": int(len(trades)), "evaluated_trades": int(len(eval_trades)), "dropped_before_first_m1": int(sum(dropped_before_m1.values())), "summary_csv": str(summary_path), "monthly_csv": str(monthly_path), "overlap_csv": str(overlap_path), "summary_json": str(json_path), "portfolio_total_r": portfolio_stats.get("total_r"), "portfolio_pf": portfolio_stats.get("profit_factor")}, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

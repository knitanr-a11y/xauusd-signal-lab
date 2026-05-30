#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""GOLD specialist 8 validation backtest / outcome-ledger builder.

This script does not send MT5 orders and does not send Discord notifications.
It builds deterministic validation ledgers that can be fed into
run_gold_specialist_8_validation_ai_review.bat.

Design points:
- All generated files are under data/gold_specialist_8 by default.
- Run outputs are split by YYYY/MM/YYYYMMDD_HHMMSS to avoid too many files in one folder.
- MT5 candle time is treated as bar open time.
- Entry time is M15 close time.
- H1/H4/D1 context is based on bars whose close_time <= signal M15 close time.
- Uses M1 first-touch if M1 is available; otherwise falls back to M5.
- Same bar TP/SL hit is resolved by --inbar-priority, default SL.
- Same M15 close + same direction candidate overlaps are aggregated into one group.
- BUY/SELL conflicts on the same M15 close are skipped.
- Component rows preserve all contributing strategy IDs for later AI review.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCHEMA_VERSION = "gold_specialist_8_validation_backtest_v1"
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_ROOT = Path("data/gold_specialist_8/verification/backtests")
DEFAULT_TRADE_OUTCOME_DIR = Path("data/gold_specialist_8/verification/trade_outcomes")
PIP_VALUE = 0.1  # GOLD: 10 pips = 1.0 price point


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    family: str
    direction: str
    priority: int
    donch_n: int | None = None
    adx_min: float = 10.0
    trigger: str = "donch_break_m15_cont"
    exit_model: str = "fixed"
    tp_pips: float | None = None
    sl_pips: float | None = None
    rr: float = 2.0
    min_tp_pips: float = 50.0
    cap_tp_pips: float = 220.0
    h4atr_mult: float = 0.55
    h1atr_mult: float = 1.5
    m15atr_mult: float = 2.5
    hours_jst: tuple[int, ...] = tuple()
    low_sl: bool = False


SPECS: list[StrategySpec] = [
    StrategySpec("BUY_H1_DONCH72_ADX18_STRUCT_RR2_MIN50_CAP220", "BUY_DONCH72", "BUY", 1, 72, 18, "donch_break_m15_cont", "struct", rr=2.0, cap_tp_pips=220),
    StrategySpec("BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220", "BUY_DONCH72", "BUY", 2, 72, 10, "donch_break_m15_cont", "h4atr", rr=1.8, h4atr_mult=0.55, cap_tp_pips=220),
    StrategySpec("SELL_H1_DONCH36_ADX10_TP150_SL75_JST20_22", "SELL_DONCH36", "SELL", 5, 36, 10, "donch_break_m15_cont", "fixed", tp_pips=150, sl_pips=75, hours_jst=(20, 21, 22)),
    StrategySpec("SELL_H1_DONCH72_ADX10_TP50_SL25_JST18_22", "SELL_DONCH72_LOW_SL", "SELL", 8, 72, 10, "donch_break_m15_cont", "fixed", tp_pips=50, sl_pips=25, hours_jst=(18, 19, 20, 21, 22), low_sl=True),
    StrategySpec("BUY_H1_DONCH20_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST01_05", "BUY_DONCH20_NIGHT", "BUY", 3, 20, 10, "donch_break_m15_cont", "blend_struct_h1atr", rr=2.0, cap_tp_pips=240, hours_jst=(1, 2, 3, 4, 5)),
    StrategySpec("BUY_H1_IMPULSE_M15_EMA20_REJECT_ADX10_H1ATR_TP15_RR2_MIN50_CAP220_JST23_04", "BUY_IMPULSE_EMA20", "BUY", 4, None, 10, "impulse_ema20_reject", "h1atr", rr=2.0, h1atr_mult=1.5, cap_tp_pips=220, hours_jst=(23, 0, 1, 2, 3, 4)),
    StrategySpec("SELL_H1H4_TREND_M15_EMA34_REJECT_ADX10_H4ATR_TP075_RR2_MIN50_CAP250_JST10_11", "SELL_EMA34_REJECT", "SELL", 6, None, 10, "ema34_reject", "h4atr075", rr=2.0, h4atr_mult=0.75, cap_tp_pips=250, hours_jst=(10, 11)),
    StrategySpec("SELL_H1H4_TREND_M15_RSI50_RECLAIM_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST23_04", "SELL_RSI50_RECLAIM", "SELL", 7, None, 10, "rsi50_reclaim", "blend_struct_h1atr", rr=2.0, cap_tp_pips=240, hours_jst=(23, 0, 1, 2, 3, 4)),
]


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdirp(path: str | Path) -> None:
    Path(wpath(path)).mkdir(parents=True, exist_ok=True)


def exists(path: str | Path) -> bool:
    return Path(wpath(path)).exists()


def write_json(path: str | Path, obj: Any) -> None:
    mkdirp(Path(path).parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    mkdirp(Path(path).parent)
    df.to_csv(wpath(path), index=False, encoding="utf-8-sig")


def now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def local_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_dir_from_root(out_root: Path, stamp: str) -> Path:
    return out_root / stamp[:4] / stamp[4:6] / stamp


def read_ohlc(path: Path, timeframe_minutes: int) -> pd.DataFrame:
    if not exists(path):
        raise FileNotFoundError(f"Missing OHLC CSV: {path}")
    try:
        df = pd.read_csv(wpath(path), encoding="utf-8-sig", sep=None, engine="python")
    except Exception:
        df = pd.read_csv(wpath(path), encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"time", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)
    df["close_time"] = df["time"] + pd.to_timedelta(timeframe_minutes, unit="m")
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    out["ema20"] = close.ewm(span=20, adjust=False).mean()
    out["ema34"] = close.ewm(span=34, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=3).mean()
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = tr.rolling(14, min_periods=3).sum()
    plus_di = 100 * pd.Series(plus_dm, index=out.index).rolling(14, min_periods=3).sum() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=out.index).rolling(14, min_periods=3).sum() / atr.replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    out["adx14"] = dx.rolling(14, min_periods=3).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=3).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=3).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi14"] = 100 - 100 / (1 + rs)
    typical = (high + low + close) / 3
    sma_tp = typical.rolling(20, min_periods=5).mean()
    mad_tp = (typical - sma_tp).abs().rolling(20, min_periods=5).mean()
    out["cci20"] = (typical - sma_tp) / (0.015 * mad_tp.replace(0, np.nan))
    for n in [20, 36, 72]:
        out[f"donch_high_{n}"] = high.rolling(n, min_periods=max(5, n // 4)).max()
        out[f"donch_low_{n}"] = low.rolling(n, min_periods=max(5, n // 4)).min()
    return out


def make_htf_context(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    base = m15.copy().sort_values("close_time")
    for tf_name, tf_df in [("h1", h1), ("h4", h4), ("d1", d1)]:
        cols = ["close_time", "open", "high", "low", "close", "ema20", "ema34", "ema50", "ema200", "atr14", "adx14", "rsi14"]
        keep = tf_df[[c for c in cols if c in tf_df.columns]].copy().sort_values("close_time")
        keep = keep.rename(columns={c: f"{tf_name}_{c}" for c in keep.columns if c != "close_time"})
        base = pd.merge_asof(base, keep, left_on="close_time", right_on="close_time", direction="backward")
    return base.sort_values("time").reset_index(drop=True)


def mt5_to_jst(ts: pd.Timestamp) -> pd.Timestamp:
    # Practical approximation used in this project: Apr-Oct as DST +6h, otherwise +7h.
    # This is deliberately centralized so live implementation can later replace it with broker-calendar logic.
    offset_hours = 6 if 4 <= int(ts.month) <= 10 else 7
    return ts + pd.Timedelta(hours=offset_hours)


def is_rollover_no_trade(ts_mt5: pd.Timestamp) -> bool:
    jst = mt5_to_jst(ts_mt5)
    if 4 <= int(ts_mt5.month) <= 10:
        return int(jst.hour) in {6, 7, 8}  # wider than previous test: includes reopen buffer
    return int(jst.hour) in {7, 8, 9}


def pips_to_price(pips: float) -> float:
    return pips * PIP_VALUE


def price_to_pips(points: float) -> float:
    return points / PIP_VALUE


def htf_up(row: pd.Series) -> bool:
    return bool(row.get("h1_close", np.nan) > row.get("h1_ema50", np.nan) and row.get("h4_close", np.nan) > row.get("h4_ema50", np.nan))


def htf_down(row: pd.Series) -> bool:
    return bool(row.get("h1_close", np.nan) < row.get("h1_ema50", np.nan) and row.get("h4_close", np.nan) < row.get("h4_ema50", np.nan))


def h1_break(row: pd.Series, spec: StrategySpec) -> bool:
    if spec.donch_n is None:
        return False
    if spec.direction == "BUY":
        high_col = f"h1_donch_high_{spec.donch_n}"
        return bool(row.get("h1_close", np.nan) >= row.get(high_col, np.inf) and row.get("h1_adx14", 0) >= spec.adx_min)
    low_col = f"h1_donch_low_{spec.donch_n}"
    return bool(row.get("h1_close", np.nan) <= row.get(low_col, -np.inf) and row.get("h1_adx14", 0) >= spec.adx_min)


def m15_continuation(row: pd.Series, spec: StrategySpec) -> bool:
    close = row.get("close", np.nan)
    open_ = row.get("open", np.nan)
    ema20 = row.get("ema20", np.nan)
    cci = row.get("cci20", np.nan)
    if spec.direction == "BUY":
        return bool(close > ema20 and close >= open_ and cci > -80)
    return bool(close < ema20 and close <= open_ and cci < 80)


def impulse_ema20_reject(row: pd.Series, spec: StrategySpec) -> bool:
    if spec.direction != "BUY":
        return False
    return bool(htf_up(row) and row.get("h1_adx14", 0) >= spec.adx_min and row.get("low", np.nan) <= row.get("ema20", np.nan) and row.get("close", np.nan) > row.get("ema20", np.nan) and row.get("close", np.nan) > row.get("open", np.nan))


def ema34_reject(row: pd.Series, spec: StrategySpec) -> bool:
    if spec.direction != "SELL":
        return False
    return bool(htf_down(row) and row.get("h1_adx14", 0) >= spec.adx_min and row.get("high", np.nan) >= row.get("ema34", np.nan) and row.get("close", np.nan) < row.get("ema34", np.nan) and row.get("close", np.nan) < row.get("open", np.nan))


def rsi50_reclaim(row: pd.Series, spec: StrategySpec) -> bool:
    if spec.direction != "SELL":
        return False
    return bool(htf_down(row) and row.get("h1_adx14", 0) >= spec.adx_min and row.get("rsi14", 100) < 50 and row.get("close", np.nan) < row.get("ema20", np.nan))


def strategy_triggered(row: pd.Series, spec: StrategySpec) -> bool:
    jst_hour = int(mt5_to_jst(pd.Timestamp(row["close_time"])).hour)
    if spec.hours_jst and jst_hour not in set(spec.hours_jst):
        return False
    if is_rollover_no_trade(pd.Timestamp(row["close_time"])):
        return False
    if spec.trigger == "donch_break_m15_cont":
        if spec.direction == "BUY" and not htf_up(row):
            return False
        if spec.direction == "SELL" and not htf_down(row):
            return False
        return h1_break(row, spec) and m15_continuation(row, spec)
    if spec.trigger == "impulse_ema20_reject":
        return impulse_ema20_reject(row, spec)
    if spec.trigger == "ema34_reject":
        return ema34_reject(row, spec)
    if spec.trigger == "rsi50_reclaim":
        return rsi50_reclaim(row, spec)
    return False


def recent_swing_pips(m15: pd.DataFrame, idx: int, direction: str, entry: float, lookback: int = 32) -> float:
    start = max(0, idx - lookback + 1)
    chunk = m15.iloc[start:idx + 1]
    if chunk.empty:
        return 120.0
    if direction == "BUY":
        dist = entry - float(chunk["low"].min())
    else:
        dist = float(chunk["high"].max()) - entry
    return max(25.0, min(120.0, price_to_pips(abs(dist))))


def compute_tp_sl(row: pd.Series, m15ctx: pd.DataFrame, idx: int, spec: StrategySpec) -> tuple[float, float, float, float]:
    entry = float(row["close"])
    if spec.exit_model == "fixed":
        tp_pips = float(spec.tp_pips or spec.min_tp_pips)
        sl_pips = float(spec.sl_pips or max(25, tp_pips / spec.rr))
    elif spec.exit_model in {"h4atr", "h4atr075"}:
        atr_pips = price_to_pips(float(row.get("h4_atr14", np.nan))) if not pd.isna(row.get("h4_atr14", np.nan)) else spec.cap_tp_pips
        tp_pips = max(spec.min_tp_pips, min(spec.cap_tp_pips, atr_pips * spec.h4atr_mult))
        sl_pips = max(25.0, min(130.0, tp_pips / spec.rr))
    elif spec.exit_model == "h1atr":
        atr_pips = price_to_pips(float(row.get("h1_atr14", np.nan))) if not pd.isna(row.get("h1_atr14", np.nan)) else spec.cap_tp_pips
        tp_pips = max(spec.min_tp_pips, min(spec.cap_tp_pips, atr_pips * spec.h1atr_mult))
        sl_pips = max(25.0, min(130.0, tp_pips / spec.rr))
    elif spec.exit_model == "struct":
        sl_pips = recent_swing_pips(m15ctx, idx, spec.direction, entry, 32)
        sl_pips = max(60.0, min(120.0, sl_pips))
        tp_pips = max(spec.min_tp_pips, min(spec.cap_tp_pips, sl_pips * spec.rr))
    elif spec.exit_model == "blend_struct_h1atr":
        swing = recent_swing_pips(m15ctx, idx, spec.direction, entry, 32)
        atr_pips = price_to_pips(float(row.get("h1_atr14", np.nan))) if not pd.isna(row.get("h1_atr14", np.nan)) else swing
        sl_pips = max(60.0, min(130.0, 0.50 * swing + 0.50 * atr_pips * 0.45))
        tp_pips = max(spec.min_tp_pips, min(spec.cap_tp_pips, sl_pips * spec.rr))
    else:
        tp_pips = spec.min_tp_pips
        sl_pips = max(25.0, tp_pips / spec.rr)
    if spec.direction == "BUY":
        tp = entry + pips_to_price(tp_pips)
        sl = entry - pips_to_price(sl_pips)
    else:
        tp = entry - pips_to_price(tp_pips)
        sl = entry + pips_to_price(sl_pips)
    return entry, tp, sl, tp_pips


def first_touch(path: pd.DataFrame, direction: str, entry: float, tp: float, sl: float, entry_time: pd.Timestamp, horizon_minutes: int, inbar_priority: str) -> dict[str, Any]:
    end_time = entry_time + pd.Timedelta(minutes=horizon_minutes)
    p = path[(path["time"] >= entry_time) & (path["time"] <= end_time)].copy()
    if p.empty:
        return {"outcome": "UNKNOWN", "close_time": "", "close_price": np.nan, "profit_r": np.nan, "bars_to_close": np.nan, "minutes_to_close": np.nan, "exit_reason": "NO_PATH"}
    stop_dist = abs(entry - sl)
    for bar_i, r in enumerate(p.itertuples(index=False), start=1):
        if direction == "BUY":
            hit_tp = float(r.high) >= tp
            hit_sl = float(r.low) <= sl
        else:
            hit_tp = float(r.low) <= tp
            hit_sl = float(r.high) >= sl
        if hit_tp and hit_sl:
            outcome = inbar_priority
            px = sl if outcome == "SL" else tp
            return {"outcome": "LOSS" if outcome == "SL" else "WIN", "close_time": r.time.strftime("%Y-%m-%d %H:%M:%S"), "close_price": px, "profit_r": -1.0 if outcome == "SL" else abs(tp - entry) / stop_dist, "bars_to_close": bar_i, "minutes_to_close": (pd.Timestamp(r.time) - entry_time).total_seconds() / 60.0, "exit_reason": "BOTH_IN_BAR_" + inbar_priority}
        if hit_tp:
            return {"outcome": "WIN", "close_time": r.time.strftime("%Y-%m-%d %H:%M:%S"), "close_price": tp, "profit_r": abs(tp - entry) / stop_dist, "bars_to_close": bar_i, "minutes_to_close": (pd.Timestamp(r.time) - entry_time).total_seconds() / 60.0, "exit_reason": "TP_FIRST"}
        if hit_sl:
            return {"outcome": "LOSS", "close_time": r.time.strftime("%Y-%m-%d %H:%M:%S"), "close_price": sl, "profit_r": -1.0, "bars_to_close": bar_i, "minutes_to_close": (pd.Timestamp(r.time) - entry_time).total_seconds() / 60.0, "exit_reason": "SL_FIRST"}
    last = p.iloc[-1]
    close = float(last["close"])
    profit_points = (close - entry) if direction == "BUY" else (entry - close)
    r_mult = profit_points / stop_dist if stop_dist > 0 else np.nan
    if r_mult > 0.05:
        outcome = "SMALL_WIN"
    elif r_mult < -0.05:
        outcome = "SMALL_LOSS"
    else:
        outcome = "BREAKEVEN"
    return {"outcome": outcome, "close_time": pd.Timestamp(last["time"]).strftime("%Y-%m-%d %H:%M:%S"), "close_price": close, "profit_r": r_mult, "bars_to_close": len(p), "minutes_to_close": (pd.Timestamp(last["time"]) - entry_time).total_seconds() / 60.0, "exit_reason": "HORIZON_CLOSE"}


def detect_components(m15ctx: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for idx, row in m15ctx.iterrows():
        if pd.isna(row.get("h1_close", np.nan)) or pd.isna(row.get("h4_close", np.nan)):
            continue
        for spec in SPECS:
            if not strategy_triggered(row, spec):
                continue
            entry, tp, sl, tp_pips = compute_tp_sl(row, m15ctx, int(idx), spec)
            sl_pips = price_to_pips(abs(entry - sl))
            signal_time = pd.Timestamp(row["close_time"])
            rows.append({
                "signal_time": signal_time.strftime("%Y-%m-%d %H:%M:%S"),
                "entry_time": signal_time.strftime("%Y-%m-%d %H:%M:%S"),
                "mt5_time": pd.Timestamp(row["time"]).strftime("%Y-%m-%d %H:%M:%S"),
                "jst_time": mt5_to_jst(signal_time).strftime("%Y-%m-%d %H:%M:%S"),
                "jst_hour": int(mt5_to_jst(signal_time).hour),
                "strategy_id": spec.strategy_id,
                "component_strategy_id": spec.strategy_id,
                "component_family": spec.family,
                "direction": spec.direction,
                "priority": spec.priority,
                "entry_price": entry,
                "tp_price": tp,
                "sl_price": sl,
                "tp_pips": tp_pips,
                "sl_pips": sl_pips,
                "exit_model": spec.exit_model,
                "low_sl": bool(spec.low_sl),
                "trigger": spec.trigger,
                "h1_adx14": row.get("h1_adx14", np.nan),
                "h1_close": row.get("h1_close", np.nan),
                "h4_close": row.get("h4_close", np.nan),
            })
    return pd.DataFrame(rows)


def aggregate_groups(components: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    groups: list[dict[str, Any]] = []
    component_out: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    if components.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    for signal_time, chunk in components.groupby("signal_time", sort=True):
        dirs = sorted(set(chunk["direction"].astype(str)))
        if len(dirs) > 1:
            bad = {"signal_time": signal_time, "reason": "BUY_SELL_CONFLICT", "directions": ",".join(dirs), "component_count": int(len(chunk))}
            conflicts.append(bad)
            continue
        direction = dirs[0]
        chunk = chunk.sort_values(["priority", "strategy_id"]).copy()
        leader = chunk.iloc[0].to_dict()
        families = set()
        votes = 0.0
        for _, r in chunk.iterrows():
            fam = str(r["component_family"])
            if fam in families:
                votes += 0.5
            else:
                votes += 1.0
                families.add(fam)
        lot = float(args.base_lot)
        if votes >= 2.5:
            lot = float(args.max_lot)
        elif votes >= 1.5:
            lot = min(float(args.max_lot), float(args.base_lot) * 2.0)
        if bool(leader.get("low_sl")):
            lot = min(lot, float(args.sell_low_sl_max_lot))
        group_id = "GS8|" + pd.Timestamp(signal_time).strftime("%Y%m%d%H%M%S") + "|" + direction
        group = {
            "group_trade_id": group_id,
            "trade_id": group_id,
            "order_key": group_id,
            "payload_key": "PAYLOAD|" + group_id,
            "signal_key": group_id,
            "symbol": "GOLD",
            "broker_symbol": "GOLD#",
            "strategy_key": leader["strategy_id"],
            "strategy_id": leader["strategy_id"],
            "leader_strategy_id": leader["strategy_id"],
            "direction": direction,
            "entry_time": leader["entry_time"],
            "entry_price": leader["entry_price"],
            "tp_price": leader["tp_price"],
            "sl_price": leader["sl_price"],
            "tp_pips": leader["tp_pips"],
            "sl_pips": leader["sl_pips"],
            "lot": lot,
            "base_lot": float(args.base_lot),
            "effective_votes": votes,
            "component_count": int(len(chunk)),
            "component_strategy_ids": ";".join(chunk["strategy_id"].astype(str).tolist()),
            "component_families": ";".join(sorted(families)),
            "review_target": "group",
        }
        groups.append(group)
        for _, r in chunk.iterrows():
            comp = r.to_dict()
            comp.update({
                "group_trade_id": group_id,
                "trade_id": group_id + "|COMP|" + str(r["strategy_id"]),
                "order_key": group_id,
                "payload_key": "PAYLOAD|" + group_id + "|COMP|" + str(r["strategy_id"]),
                "signal_key": group_id + "|" + str(r["strategy_id"]),
                "symbol": "GOLD",
                "broker_symbol": "GOLD#",
                "strategy_key": str(r["strategy_id"]),
                "strategy_id": str(r["strategy_id"]),
                "is_leader": bool(str(r["strategy_id"]) == str(leader["strategy_id"])),
                "leader_strategy_id": leader["strategy_id"],
                "group_effective_votes": votes,
                "group_lot": lot,
                "review_target": "component",
            })
            component_out.append(comp)
    return pd.DataFrame(groups), pd.DataFrame(component_out), pd.DataFrame(conflicts)


def attach_outcomes(groups: pd.DataFrame, components: pd.DataFrame, path: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    if groups.empty:
        return groups, components
    group_rows = []
    for _, g in groups.iterrows():
        entry_time = pd.Timestamp(g["entry_time"])
        res = first_touch(path, str(g["direction"]), float(g["entry_price"]), float(g["tp_price"]), float(g["sl_price"]), entry_time, int(args.horizon_minutes), args.inbar_priority)
        out = g.to_dict()
        out.update(res)
        out["group_outcome"] = out["outcome"]
        out["group_profit_r"] = out["profit_r"]
        group_rows.append(out)
    groups_done = pd.DataFrame(group_rows)
    comp_rows = []
    group_lookup = {r["group_trade_id"]: r for r in group_rows}
    for _, c in components.iterrows():
        entry_time = pd.Timestamp(c["entry_time"])
        res = first_touch(path, str(c["direction"]), float(c["entry_price"]), float(c["tp_price"]), float(c["sl_price"]), entry_time, int(args.horizon_minutes), args.inbar_priority)
        out = c.to_dict()
        g = group_lookup.get(out["group_trade_id"], {})
        out.update({
            "group_outcome": g.get("group_outcome", ""),
            "group_profit_r": g.get("group_profit_r", np.nan),
            "standalone_virtual_outcome": res.get("outcome"),
            "standalone_virtual_profit_r": res.get("profit_r"),
            "standalone_virtual_close_time": res.get("close_time"),
            "standalone_virtual_close_price": res.get("close_price"),
            "outcome": res.get("outcome"),
            "profit_r": res.get("profit_r"),
            "close_time": res.get("close_time"),
            "close_price": res.get("close_price"),
            "exit_reason": res.get("exit_reason"),
        })
        comp_rows.append(out)
    return groups_done, pd.DataFrame(comp_rows)


def summarize(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for k, g in df.groupby(key, dropna=False):
        r = pd.to_numeric(g.get("profit_r"), errors="coerce")
        wins = int((r > 0).sum())
        losses = int((r < 0).sum())
        gross_win = float(r[r > 0].sum())
        gross_loss = float(-r[r < 0].sum())
        pf = gross_win / gross_loss if gross_loss > 0 else (math.inf if gross_win > 0 else 0.0)
        rows.append({key: k, "trades": int(len(g)), "wins": wins, "losses": losses, "win_rate": wins / len(g) if len(g) else 0, "total_r": float(r.sum()), "avg_r": float(r.mean()), "profit_factor": pf})
    return pd.DataFrame(rows).sort_values(["profit_factor", "total_r"], ascending=[False, False])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GOLD specialist 8 validation trade outcome ledgers.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--trade-outcome-dir", type=Path, default=DEFAULT_TRADE_OUTCOME_DIR)
    p.add_argument("--run-stamp", default="")
    p.add_argument("--m1-file", default="goldsharp_m1.csv")
    p.add_argument("--m5-file", default="goldsharp_m5.csv")
    p.add_argument("--m15-file", default="goldsharp_m15.csv")
    p.add_argument("--h1-file", default="goldsharp_h1.csv")
    p.add_argument("--h4-file", default="goldsharp_h4.csv")
    p.add_argument("--d1-file", default="goldsharp_d1.csv")
    p.add_argument("--horizon-minutes", type=int, default=2880)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--max-lot", type=float, default=0.03)
    p.add_argument("--sell-low-sl-max-lot", type=float, default=0.02)
    p.add_argument("--start", default="")
    p.add_argument("--end", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    stamp = args.run_stamp.strip() or local_stamp()
    out_root = args.out_root
    run_dir = run_dir_from_root(out_root, stamp)
    mkdirp(run_dir)
    mkdirp(args.trade_outcome_dir)
    summary_json = run_dir / "gold_specialist_8_validation_backtest_summary.json"
    latest_summary_json = out_root / "latest_gold_specialist_8_validation_backtest_summary.json"
    latest_run_dir_txt = out_root / "latest_run_dir.txt"

    m1_path = args.csv_dir / args.m1_file
    path_tf = "m1"
    try:
        path_df = read_ohlc(m1_path, 1)
    except Exception:
        path_tf = "m5"
        path_df = read_ohlc(args.csv_dir / args.m5_file, 5)
    m15 = add_indicators(read_ohlc(args.csv_dir / args.m15_file, 15))
    h1 = add_indicators(read_ohlc(args.csv_dir / args.h1_file, 60))
    h4 = add_indicators(read_ohlc(args.csv_dir / args.h4_file, 240))
    d1 = add_indicators(read_ohlc(args.csv_dir / args.d1_file, 1440))
    if args.start:
        m15 = m15[m15["close_time"] >= pd.Timestamp(args.start)].copy()
    if args.end:
        m15 = m15[m15["close_time"] <= pd.Timestamp(args.end)].copy()
    max_entry = path_df["time"].max() - pd.Timedelta(minutes=int(args.horizon_minutes))
    m15 = m15[m15["close_time"] <= max_entry].copy()
    m15ctx = make_htf_context(m15, h1, h4, d1)
    components_raw = detect_components(m15ctx, args)
    groups, components, conflicts = aggregate_groups(components_raw, args)
    groups_done, components_done = attach_outcomes(groups, components, path_df, args)

    group_csv = run_dir / "gold_specialist_8_group_trade_ledger_validation.csv"
    component_csv = run_dir / "gold_specialist_8_component_signal_ledger_validation.csv"
    outcome_csv = run_dir / "gold_specialist_8_validation_trade_outcome_ledger.csv"
    conflicts_csv = run_dir / "gold_specialist_8_conflict_skipped_signals.csv"
    strategy_summary_csv = run_dir / "gold_specialist_8_strategy_summary.csv"
    component_summary_csv = run_dir / "gold_specialist_8_component_strategy_summary.csv"
    write_csv(groups_done, group_csv)
    write_csv(components_done, component_csv)
    review_input = pd.concat([groups_done, components_done], ignore_index=True, sort=False) if not groups_done.empty or not components_done.empty else pd.DataFrame()
    write_csv(review_input, outcome_csv)
    write_csv(conflicts, conflicts_csv)
    write_csv(summarize(groups_done, "leader_strategy_id") if not groups_done.empty else pd.DataFrame(), strategy_summary_csv)
    write_csv(summarize(components_done, "strategy_id") if not components_done.empty else pd.DataFrame(), component_summary_csv)

    latest_outcome = args.trade_outcome_dir / "gold_specialist_8_validation_trade_outcome_ledger.csv"
    latest_group = args.trade_outcome_dir / "gold_specialist_8_group_trade_ledger_validation.csv"
    latest_component = args.trade_outcome_dir / "gold_specialist_8_component_signal_ledger_validation.csv"
    write_csv(review_input, latest_outcome)
    write_csv(groups_done, latest_group)
    write_csv(components_done, latest_component)

    no_future = {
        "h1_future_violations": int((m15ctx["h1_close_time"] > m15ctx["close_time"]).sum()) if "h1_close_time" in m15ctx.columns else 0,
        "h4_future_violations": int((m15ctx["h4_close_time"] > m15ctx["close_time"]).sum()) if "h4_close_time" in m15ctx.columns else 0,
        "d1_future_violations": int((m15ctx["d1_close_time"] > m15ctx["close_time"]).sum()) if "d1_close_time" in m15ctx.columns else 0,
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": now_text(),
        "cycle_ok": True,
        "run_dir": str(run_dir),
        "latest_validation_trade_outcome_csv": str(latest_outcome),
        "path_timeframe_used_for_first_touch": path_tf,
        "key_metrics": {
            "m15_rows_used": int(len(m15ctx)),
            "raw_component_signals": int(len(components_raw)),
            "groups": int(len(groups_done)),
            "component_rows": int(len(components_done)),
            "review_input_rows": int(len(review_input)),
            "buy_sell_conflict_skipped_groups": int(len(conflicts)),
        },
        "no_future_htf_audit": no_future,
        "outputs": {
            "group_csv": str(group_csv),
            "component_csv": str(component_csv),
            "outcome_csv": str(outcome_csv),
            "conflicts_csv": str(conflicts_csv),
            "strategy_summary_csv": str(strategy_summary_csv),
            "component_summary_csv": str(component_summary_csv),
        },
        "safety": {"mt5_order_send": False, "discord_send": False, "ai_call": False},
    }
    write_json(summary_json, summary)
    write_json(latest_summary_json, summary)
    with open(wpath(latest_run_dir_txt), "w", encoding="utf-8", newline="") as f:
        f.write(str(run_dir))
    print(json.dumps({"cycle_ok": True, "run_dir": str(run_dir), "key_metrics": summary["key_metrics"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

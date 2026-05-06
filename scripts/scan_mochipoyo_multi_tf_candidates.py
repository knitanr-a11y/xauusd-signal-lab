#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mochipoyo-style multi-timeframe candidate scanner.

This scanner translates the guide's discretionary flow into auditable,
backtest-ready candidate rows:

1. Read GOLD/BTC OHLC CSVs.
2. Build indicators per timeframe.
3. Optionally resample D1 into W1/MN1 later; first version uses M1/M5/M15/H1/H4/D1.
4. Join context timeframe to base timeframe by confirmed close time only.
5. Score context side:
   - EMA20/30/40 order and slope
   - Granville buy/sell 2 and 3 approximations
   - RCI zone and turn
   - MACD divergence / hidden divergence on confirmed pivots
   - volatility and EMA-band filters
6. Score base side:
   - lower timeframe EMA order
   - pullback/retrace toward EMA band
   - RCI zone and turn
   - MACD divergence / hidden divergence on confirmed pivots
7. Output candidate rows with timing audit columns.

Safety rules:
- context_close_time <= base_close_time
- pivot_confirmed_time <= signal_close_time
- entry_time >= signal_close_time
- no unconfirmed higher timeframe bar is used
- ZigZag pivots are usable only after depth bars have closed

This script does NOT adopt signals and does NOT send notifications.
It only produces candidate CSVs for review and later first-touch backtesting.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


TF_MINUTES: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

DEFAULT_GOLD_PAIRS = [
    {"pair_name": "GOLD_H1_M1_SCALP", "style": "scalp", "context_tf": "H1", "base_tf": "M1"},
    {"pair_name": "GOLD_H4_M5_SCALP", "style": "scalp", "context_tf": "H4", "base_tf": "M5"},
    {"pair_name": "GOLD_H4_M15_DAYTRADE", "style": "daytrade", "context_tf": "H4", "base_tf": "M15"},
    {"pair_name": "GOLD_D1_H1_DAYTRADE", "style": "daytrade", "context_tf": "D1", "base_tf": "H1"},
]

DEFAULT_BTC_PAIRS = [
    {"pair_name": "BTC_H1_M1_SCALP", "style": "scalp", "context_tf": "H1", "base_tf": "M1"},
    {"pair_name": "BTC_H4_M5_SCALP", "style": "scalp", "context_tf": "H4", "base_tf": "M5"},
    {"pair_name": "BTC_H4_M15_DAYTRADE", "style": "daytrade", "context_tf": "H4", "base_tf": "M15"},
    {"pair_name": "BTC_D1_H1_DAYTRADE", "style": "daytrade", "context_tf": "D1", "base_tf": "H1"},
]


@dataclass(frozen=True)
class PivotEvent:
    pivot_idx: int
    confirm_idx: int
    kind: str
    price: float
    div_type: str
    prev_pivot_idx: int | None
    prev_price: float | None
    pivot_macd: float | None
    prev_pivot_macd: float | None


@dataclass(frozen=True)
class CandidateRow:
    symbol: str
    pair_name: str
    style: str
    context_tf: str
    base_tf: str
    direction: str
    candidate_rank: str
    total_score: float
    context_score: float
    base_score: float
    base_time: str
    base_close_time: str
    signal_time: str
    signal_close_time: str
    entry_time: str
    entry_price: float
    context_time: str
    context_close_time: str
    context_granville_type: str
    context_bias: str
    context_ema_order: str
    context_close: float
    context_ema20: float
    context_ema30: float
    context_ema40: float
    context_rci9: float
    context_rci14: float
    context_rci18: float
    context_macd: float
    context_macd_hist: float
    context_macd_div_type: str
    context_pivot_time: str
    context_pivot_confirmed_time: str
    base_ema_order: str
    base_rci9: float
    base_rci14: float
    base_rci18: float
    base_macd: float
    base_macd_hist: float
    base_macd_div_type: str
    base_pivot_time: str
    base_pivot_confirmed_time: str
    base_open: float
    base_high: float
    base_low: float
    base_close: float
    audit_context_confirmed: bool
    audit_context_confirm_lag_min: float
    audit_base_pivot_confirmed: bool
    audit_context_pivot_confirmed: bool
    audit_entry_after_signal: bool
    reason_text: str


def timeframe_minutes(tf: str) -> int:
    key = str(tf).upper()
    if key not in TF_MINUTES:
        raise ValueError(f"Unsupported timeframe: {tf}")
    return TF_MINUTES[key]


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


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def rci_series(close: pd.Series, period: int) -> pd.Series:
    arr = close.to_numpy(dtype=float)
    res = np.full(len(arr), np.nan)
    t_rank = np.arange(1, period + 1, dtype=float)
    denom = period * (period * period - 1)
    for i in range(period - 1, len(arr)):
        w = arr[i - period + 1 : i + 1]
        if np.isnan(w).any():
            continue
        p_rank = pd.Series(w).rank(method="average").to_numpy(dtype=float)
        d = t_rank - p_rank
        res[i] = (1.0 - 6.0 * np.sum(d * d) / denom) * 100.0
    return pd.Series(res, index=close.index)


def finite_float(value: object) -> float:
    try:
        out = float(value)
    except Exception:
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def as_time_str(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(pd.Timestamp(value))


def add_indicators(df: pd.DataFrame, tf: str, *, zigzag_depth: int, zigzag_deviation: float, zigzag_deviation_mode: str, point_size: float, zigzag_backstep: int) -> pd.DataFrame:
    out = df.copy()
    out["close_time"] = out["time"] + pd.to_timedelta(timeframe_minutes(tf), unit="m")
    out["ema20"] = ema(out["close"], 20)
    out["ema30"] = ema(out["close"], 30)
    out["ema40"] = ema(out["close"], 40)
    out["ema20_slope"] = out["ema20"] - out["ema20"].shift(3)
    out["ema30_slope"] = out["ema30"] - out["ema30"].shift(3)
    out["ema40_slope"] = out["ema40"] - out["ema40"].shift(3)
    bull = (out["ema20"] > out["ema30"]) & (out["ema30"] > out["ema40"])
    bear = (out["ema20"] < out["ema30"]) & (out["ema30"] < out["ema40"])
    out["ema_order"] = np.where(bull, "BULL", np.where(bear, "BEAR", "MIXED"))
    out["ema_band_top"] = out[["ema20", "ema30", "ema40"]].max(axis=1)
    out["ema_band_bottom"] = out[["ema20", "ema30", "ema40"]].min(axis=1)
    out["ema_band_mid"] = out[["ema20", "ema30", "ema40"]].mean(axis=1)
    out["ema_band_width"] = out["ema_band_top"] - out["ema_band_bottom"]
    out["atr14"] = atr(out, 14)
    out["ema_band_width_atr"] = out["ema_band_width"] / out["atr14"].replace(0, np.nan)
    out["close_to_ema20_atr"] = (out["close"] - out["ema20"]) / out["atr14"].replace(0, np.nan)
    out["close_to_ema40_atr"] = (out["close"] - out["ema40"]) / out["atr14"].replace(0, np.nan)
    out["macd"] = ema(out["close"], 6) - ema(out["close"], 13)
    out["macd_signal"] = ema(out["macd"], 4)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["rci9"] = rci_series(out["close"], 9)
    out["rci14"] = rci_series(out["close"], 14)
    out["rci18"] = rci_series(out["close"], 18)
    out["rci9_delta"] = out["rci9"] - out["rci9"].shift(1)
    out["rci14_delta"] = out["rci14"] - out["rci14"].shift(1)

    pivots = build_confirmed_pivot_events(out, zigzag_depth, zigzag_deviation, zigzag_deviation_mode, point_size, zigzag_backstep)
    out = attach_latest_pivot_events(out, pivots)
    return out


def local_extrema(df: pd.DataFrame, depth: int) -> pd.DataFrame:
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    rows: list[dict] = []
    for i in range(depth, len(df) - depth):
        hw = highs[i - depth : i + depth + 1]
        lw = lows[i - depth : i + depth + 1]
        if highs[i] == np.nanmax(hw):
            rows.append({"idx": i, "kind": "HIGH", "price": highs[i]})
        if lows[i] == np.nanmin(lw):
            rows.append({"idx": i, "kind": "LOW", "price": lows[i]})
    return pd.DataFrame(rows)


def deviation_threshold(price: float, deviation: float, mode: str, point_size: float) -> float:
    if mode == "price":
        return deviation
    if mode == "percent":
        return abs(price) * deviation / 100.0
    if mode == "points":
        return deviation * point_size
    raise ValueError(f"Unsupported deviation mode: {mode}")


def prune_zigzag(raw: pd.DataFrame, *, deviation: float, mode: str, point_size: float, backstep: int) -> pd.DataFrame:
    if raw.empty:
        return raw
    raw = raw.sort_values(["idx", "kind"], kind="mergesort").reset_index(drop=True)
    kept: list[dict] = []
    for row in raw.to_dict("records"):
        if not kept:
            kept.append(row)
            continue
        last = kept[-1]
        gap = int(row["idx"]) - int(last["idx"])
        if row["kind"] == last["kind"]:
            if row["kind"] == "HIGH" and float(row["price"]) > float(last["price"]):
                kept[-1] = row
            elif row["kind"] == "LOW" and float(row["price"]) < float(last["price"]):
                kept[-1] = row
            continue
        if gap < backstep:
            continue
        move = abs(float(row["price"]) - float(last["price"]))
        if move >= deviation_threshold(float(last["price"]), deviation, mode, point_size):
            kept.append(row)
    out = pd.DataFrame(kept)
    if out.empty:
        return out
    return out.sort_values("idx", kind="mergesort").reset_index(drop=True)


def divergence_type(kind: str, prev_price: float, price: float, prev_macd: float, macd: float) -> str:
    if not all(math.isfinite(v) for v in [prev_price, price, prev_macd, macd]):
        return ""
    if kind == "LOW":
        if price < prev_price and macd > prev_macd:
            return "regular_bullish"
        if price > prev_price and macd < prev_macd:
            return "hidden_bullish"
    if kind == "HIGH":
        if price > prev_price and macd < prev_macd:
            return "regular_bearish"
        if price < prev_price and macd > prev_macd:
            return "hidden_bearish"
    return ""


def build_confirmed_pivot_events(df: pd.DataFrame, depth: int, deviation: float, mode: str, point_size: float, backstep: int) -> list[PivotEvent]:
    raw = local_extrema(df, depth)
    zz = prune_zigzag(raw, deviation=deviation, mode=mode, point_size=point_size, backstep=backstep)
    if zz.empty:
        return []
    events: list[PivotEvent] = []
    prev_by_kind: dict[str, dict] = {}
    for p in zz.to_dict("records"):
        idx = int(p["idx"])
        confirm_idx = idx + depth
        if confirm_idx >= len(df):
            continue
        kind = str(p["kind"])
        prev = prev_by_kind.get(kind)
        prev_by_kind[kind] = p
        prev_idx = int(prev["idx"]) if prev is not None else None
        prev_price = float(prev["price"]) if prev is not None else None
        pivot_macd = finite_float(df.iloc[idx].get("macd"))
        prev_macd = finite_float(df.iloc[prev_idx].get("macd")) if prev_idx is not None else None
        div = divergence_type(kind, prev_price if prev_price is not None else float("nan"), float(p["price"]), prev_macd if prev_macd is not None else float("nan"), pivot_macd)
        events.append(
            PivotEvent(
                pivot_idx=idx,
                confirm_idx=confirm_idx,
                kind=kind,
                price=float(p["price"]),
                div_type=div,
                prev_pivot_idx=prev_idx,
                prev_price=prev_price,
                pivot_macd=pivot_macd,
                prev_pivot_macd=prev_macd,
            )
        )
    return events


def attach_latest_pivot_events(df: pd.DataFrame, events: list[PivotEvent]) -> pd.DataFrame:
    out = df.copy()
    cols = [
        "latest_low_pivot_idx", "latest_low_confirm_idx", "latest_low_price", "latest_low_div_type", "latest_low_pivot_time", "latest_low_confirm_time",
        "latest_high_pivot_idx", "latest_high_confirm_idx", "latest_high_price", "latest_high_div_type", "latest_high_pivot_time", "latest_high_confirm_time",
    ]
    for c in cols:
        out[c] = np.nan if c.endswith("idx") or c.endswith("price") else ""

    latest_low: PivotEvent | None = None
    latest_high: PivotEvent | None = None
    events_by_confirm: dict[int, list[PivotEvent]] = {}
    for ev in events:
        events_by_confirm.setdefault(ev.confirm_idx, []).append(ev)

    for i in range(len(out)):
        for ev in events_by_confirm.get(i, []):
            if ev.kind == "LOW":
                latest_low = ev
            elif ev.kind == "HIGH":
                latest_high = ev
        if latest_low is not None:
            out.at[i, "latest_low_pivot_idx"] = latest_low.pivot_idx
            out.at[i, "latest_low_confirm_idx"] = latest_low.confirm_idx
            out.at[i, "latest_low_price"] = latest_low.price
            out.at[i, "latest_low_div_type"] = latest_low.div_type
            out.at[i, "latest_low_pivot_time"] = as_time_str(out.iloc[latest_low.pivot_idx]["time"])
            out.at[i, "latest_low_confirm_time"] = as_time_str(out.iloc[latest_low.confirm_idx]["close_time"])
        if latest_high is not None:
            out.at[i, "latest_high_pivot_idx"] = latest_high.pivot_idx
            out.at[i, "latest_high_confirm_idx"] = latest_high.confirm_idx
            out.at[i, "latest_high_price"] = latest_high.price
            out.at[i, "latest_high_div_type"] = latest_high.div_type
            out.at[i, "latest_high_pivot_time"] = as_time_str(out.iloc[latest_high.pivot_idx]["time"])
            out.at[i, "latest_high_confirm_time"] = as_time_str(out.iloc[latest_high.confirm_idx]["close_time"])
    return out


def confirmed_join(base: pd.DataFrame, context: pd.DataFrame, base_tf: str, context_tf: str) -> pd.DataFrame:
    b = base.copy().sort_values("close_time")
    c = context.copy().sort_values("close_time")
    context_cols = [
        "time", "close_time", "open", "high", "low", "close",
        "ema20", "ema30", "ema40", "ema20_slope", "ema30_slope", "ema40_slope", "ema_order",
        "ema_band_top", "ema_band_bottom", "ema_band_mid", "ema_band_width", "ema_band_width_atr",
        "close_to_ema20_atr", "close_to_ema40_atr", "atr14",
        "macd", "macd_signal", "macd_hist", "rci9", "rci14", "rci18", "rci9_delta", "rci14_delta",
        "latest_low_pivot_time", "latest_low_confirm_time", "latest_low_div_type", "latest_low_price",
        "latest_high_pivot_time", "latest_high_confirm_time", "latest_high_div_type", "latest_high_price",
    ]
    context_cols = [c0 for c0 in context_cols if c0 in c.columns]
    c = c[context_cols].rename(columns={col: f"context_{col}" for col in context_cols})
    out = pd.merge_asof(
        b,
        c,
        left_on="close_time",
        right_on="context_close_time",
        direction="backward",
    )
    return out.sort_values("time", kind="mergesort").reset_index(drop=True)


def score_context(row: pd.Series, direction: str, *, rci_zone: float, min_atr: float) -> tuple[float, str, str, list[str]]:
    score = 0.0
    reasons: list[str] = []
    bias = "NONE"
    granville = ""
    close = finite_float(row.get("context_close"))
    ema20 = finite_float(row.get("context_ema20"))
    ema30 = finite_float(row.get("context_ema30"))
    ema40 = finite_float(row.get("context_ema40"))
    atr14 = finite_float(row.get("context_atr14"))
    order = str(row.get("context_ema_order"))
    e20s = finite_float(row.get("context_ema20_slope"))
    e30s = finite_float(row.get("context_ema30_slope"))
    band_top = finite_float(row.get("context_ema_band_top"))
    band_bottom = finite_float(row.get("context_ema_band_bottom"))
    band_width_atr = finite_float(row.get("context_ema_band_width_atr"))
    rci9 = finite_float(row.get("context_rci9"))
    rci14 = finite_float(row.get("context_rci14"))
    rci9_delta = finite_float(row.get("context_rci9_delta"))
    rci14_delta = finite_float(row.get("context_rci14_delta"))
    div_low = str(row.get("context_latest_low_div_type") or "")
    div_high = str(row.get("context_latest_high_div_type") or "")

    if not all(math.isfinite(v) for v in [close, ema20, ema30, ema40]):
        return 0.0, bias, granville, ["context_indicator_nan"]

    if math.isfinite(atr14) and atr14 < min_atr:
        score -= 2.0
        reasons.append("context_low_atr")
    if math.isfinite(band_width_atr) and band_width_atr < 0.05:
        score -= 1.5
        reasons.append("context_ema_dense")

    near_band = math.isfinite(band_top) and math.isfinite(band_bottom) and band_bottom <= close <= band_top
    slightly_near_band = False
    if math.isfinite(atr14) and atr14 > 0 and math.isfinite(band_top) and math.isfinite(band_bottom):
        slightly_near_band = (band_bottom - 0.35 * atr14) <= close <= (band_top + 0.35 * atr14)

    if direction == "BUY":
        if order == "BULL":
            score += 2.0; reasons.append("context_ema_bull")
        if e20s > 0 and e30s > 0:
            score += 1.0; reasons.append("context_ema_slope_up")
        if slightly_near_band:
            score += 1.0; reasons.append("context_pullback_to_ema_band")
        if order == "BULL" and slightly_near_band:
            score += 2.0; granville = "BUY_3"; reasons.append("granville_buy_3")
        elif close > ema20 and e20s > 0 and e30s >= 0:
            score += 1.0; granville = "BUY_2"; reasons.append("granville_buy_2_like")
        if rci9 <= -rci_zone or rci14 <= -rci_zone:
            score += 1.0; reasons.append("context_rci_lower_zone")
        if rci9_delta > 0 or rci14_delta > 0:
            score += 1.0; reasons.append("context_rci_turn_up")
        if div_low == "hidden_bullish":
            score += 2.0; reasons.append("context_hidden_bullish")
        elif div_low == "regular_bullish":
            score += 1.0; reasons.append("context_regular_bullish")
        bias = "BUY" if score > 0 else "NONE"
    else:
        if order == "BEAR":
            score += 2.0; reasons.append("context_ema_bear")
        if e20s < 0 and e30s < 0:
            score += 1.0; reasons.append("context_ema_slope_down")
        if slightly_near_band:
            score += 1.0; reasons.append("context_retrace_to_ema_band")
        if order == "BEAR" and slightly_near_band:
            score += 2.0; granville = "SELL_3"; reasons.append("granville_sell_3")
        elif close < ema20 and e20s < 0 and e30s <= 0:
            score += 1.0; granville = "SELL_2"; reasons.append("granville_sell_2_like")
        if rci9 >= rci_zone or rci14 >= rci_zone:
            score += 1.0; reasons.append("context_rci_upper_zone")
        if rci9_delta < 0 or rci14_delta < 0:
            score += 1.0; reasons.append("context_rci_turn_down")
        if div_high == "hidden_bearish":
            score += 2.0; reasons.append("context_hidden_bearish")
        elif div_high == "regular_bearish":
            score += 1.0; reasons.append("context_regular_bearish")
        bias = "SELL" if score > 0 else "NONE"

    return score, bias, granville, reasons


def score_base(row: pd.Series, direction: str, *, rci_zone: float) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []
    order = str(row.get("ema_order"))
    close = finite_float(row.get("close"))
    atr14 = finite_float(row.get("atr14"))
    band_top = finite_float(row.get("ema_band_top"))
    band_bottom = finite_float(row.get("ema_band_bottom"))
    rci9 = finite_float(row.get("rci9"))
    rci14 = finite_float(row.get("rci14"))
    rci9_delta = finite_float(row.get("rci9_delta"))
    rci14_delta = finite_float(row.get("rci14_delta"))
    div_low = str(row.get("latest_low_div_type") or "")
    div_high = str(row.get("latest_high_div_type") or "")
    base_div = ""

    if not math.isfinite(close):
        return 0.0, base_div, ["base_close_nan"]

    slightly_near_band = False
    if math.isfinite(atr14) and atr14 > 0 and math.isfinite(band_top) and math.isfinite(band_bottom):
        slightly_near_band = (band_bottom - 0.35 * atr14) <= close <= (band_top + 0.35 * atr14)

    if direction == "BUY":
        if order == "BULL":
            score += 1.0; reasons.append("base_ema_bull")
        if slightly_near_band:
            score += 1.0; reasons.append("base_pullback_to_ema_band")
        if rci9 <= -rci_zone:
            score += 1.0; reasons.append("base_rci9_lower_zone")
        if rci14 <= -rci_zone:
            score += 1.0; reasons.append("base_rci14_lower_zone")
        if rci9_delta > 0 or rci14_delta > 0:
            score += 1.0; reasons.append("base_rci_turn_up")
        if div_low == "hidden_bullish":
            score += 2.0; base_div = div_low; reasons.append("base_hidden_bullish")
        elif div_low == "regular_bullish":
            score += 1.5; base_div = div_low; reasons.append("base_regular_bullish")
    else:
        if order == "BEAR":
            score += 1.0; reasons.append("base_ema_bear")
        if slightly_near_band:
            score += 1.0; reasons.append("base_retrace_to_ema_band")
        if rci9 >= rci_zone:
            score += 1.0; reasons.append("base_rci9_upper_zone")
        if rci14 >= rci_zone:
            score += 1.0; reasons.append("base_rci14_upper_zone")
        if rci9_delta < 0 or rci14_delta < 0:
            score += 1.0; reasons.append("base_rci_turn_down")
        if div_high == "hidden_bearish":
            score += 2.0; base_div = div_high; reasons.append("base_hidden_bearish")
        elif div_high == "regular_bearish":
            score += 1.5; base_div = div_high; reasons.append("base_regular_bearish")
    return score, base_div, reasons


def rank_from_score(total_score: float, a_threshold: float, b_threshold: float, c_threshold: float) -> str:
    if total_score >= a_threshold:
        return "A"
    if total_score >= b_threshold:
        return "B"
    if total_score >= c_threshold:
        return "C"
    return ""


def next_entry_time(df: pd.DataFrame, idx: int) -> tuple[str, float]:
    next_idx = idx + 1
    if next_idx < len(df):
        return as_time_str(df.iloc[next_idx]["time"]), finite_float(df.iloc[next_idx]["open"])
    return as_time_str(df.iloc[idx]["close_time"]), finite_float(df.iloc[idx]["close"])


def context_div_for_direction(row: pd.Series, direction: str) -> tuple[str, str, str]:
    if direction == "BUY":
        return (
            str(row.get("context_latest_low_div_type") or ""),
            str(row.get("context_latest_low_pivot_time") or ""),
            str(row.get("context_latest_low_confirm_time") or ""),
        )
    return (
        str(row.get("context_latest_high_div_type") or ""),
        str(row.get("context_latest_high_pivot_time") or ""),
        str(row.get("context_latest_high_confirm_time") or ""),
    )


def base_pivot_for_direction(row: pd.Series, direction: str) -> tuple[str, str, str]:
    if direction == "BUY":
        return (
            str(row.get("latest_low_div_type") or ""),
            str(row.get("latest_low_pivot_time") or ""),
            str(row.get("latest_low_confirm_time") or ""),
        )
    return (
        str(row.get("latest_high_div_type") or ""),
        str(row.get("latest_high_pivot_time") or ""),
        str(row.get("latest_high_confirm_time") or ""),
    )


def parse_ts_or_nat(value: object) -> pd.Timestamp:
    try:
        return pd.Timestamp(value)
    except Exception:
        return pd.NaT


def scan_pair(joined: pd.DataFrame, pair: dict, args: argparse.Namespace) -> list[CandidateRow]:
    rows: list[CandidateRow] = []
    for i, row in joined.iterrows():
        if i < args.min_warmup_bars:
            continue
        for direction in ["BUY", "SELL"]:
            c_score, bias, granville, c_reasons = score_context(row, direction, rci_zone=args.rci_zone, min_atr=args.min_context_atr)
            if c_score < args.min_context_score:
                continue
            b_score, base_div, b_reasons = score_base(row, direction, rci_zone=args.rci_zone)
            total = c_score + b_score
            rank = rank_from_score(total, args.rank_a, args.rank_b, args.rank_c)
            if not rank:
                continue
            entry_time, entry_price = next_entry_time(joined, i)
            context_div, context_pivot_time, context_pivot_confirm_time = context_div_for_direction(row, direction)
            base_div2, base_pivot_time, base_pivot_confirm_time = base_pivot_for_direction(row, direction)
            if not base_div:
                base_div = base_div2

            base_close_time = parse_ts_or_nat(row.get("close_time"))
            context_close_time = parse_ts_or_nat(row.get("context_close_time"))
            signal_close_time = base_close_time
            entry_ts = parse_ts_or_nat(entry_time)
            base_pivot_confirm_ts = parse_ts_or_nat(base_pivot_confirm_time)
            context_pivot_confirm_ts = parse_ts_or_nat(context_pivot_confirm_time)

            audit_context_confirmed = bool(pd.notna(context_close_time) and pd.notna(base_close_time) and context_close_time <= base_close_time)
            lag_min = float((base_close_time - context_close_time).total_seconds() / 60.0) if audit_context_confirmed else float("nan")
            audit_base_pivot_confirmed = bool((base_pivot_confirm_time == "") or (pd.notna(base_pivot_confirm_ts) and base_pivot_confirm_ts <= signal_close_time))
            audit_context_pivot_confirmed = bool((context_pivot_confirm_time == "") or (pd.notna(context_pivot_confirm_ts) and context_pivot_confirm_ts <= signal_close_time))
            audit_entry_after_signal = bool(pd.notna(entry_ts) and pd.notna(signal_close_time) and entry_ts >= signal_close_time)

            if args.require_divergence:
                if not context_div and not base_div:
                    continue

            reason = ";".join(c_reasons + b_reasons)
            rows.append(
                CandidateRow(
                    symbol=args.symbol,
                    pair_name=pair["pair_name"],
                    style=pair["style"],
                    context_tf=pair["context_tf"],
                    base_tf=pair["base_tf"],
                    direction=direction,
                    candidate_rank=rank,
                    total_score=round(total, 3),
                    context_score=round(c_score, 3),
                    base_score=round(b_score, 3),
                    base_time=as_time_str(row.get("time")),
                    base_close_time=as_time_str(row.get("close_time")),
                    signal_time=as_time_str(row.get("time")),
                    signal_close_time=as_time_str(row.get("close_time")),
                    entry_time=entry_time,
                    entry_price=entry_price,
                    context_time=as_time_str(row.get("context_time")),
                    context_close_time=as_time_str(row.get("context_close_time")),
                    context_granville_type=granville,
                    context_bias=bias,
                    context_ema_order=str(row.get("context_ema_order") or ""),
                    context_close=finite_float(row.get("context_close")),
                    context_ema20=finite_float(row.get("context_ema20")),
                    context_ema30=finite_float(row.get("context_ema30")),
                    context_ema40=finite_float(row.get("context_ema40")),
                    context_rci9=finite_float(row.get("context_rci9")),
                    context_rci14=finite_float(row.get("context_rci14")),
                    context_rci18=finite_float(row.get("context_rci18")),
                    context_macd=finite_float(row.get("context_macd")),
                    context_macd_hist=finite_float(row.get("context_macd_hist")),
                    context_macd_div_type=context_div,
                    context_pivot_time=context_pivot_time,
                    context_pivot_confirmed_time=context_pivot_confirm_time,
                    base_ema_order=str(row.get("ema_order") or ""),
                    base_rci9=finite_float(row.get("rci9")),
                    base_rci14=finite_float(row.get("rci14")),
                    base_rci18=finite_float(row.get("rci18")),
                    base_macd=finite_float(row.get("macd")),
                    base_macd_hist=finite_float(row.get("macd_hist")),
                    base_macd_div_type=base_div,
                    base_pivot_time=base_pivot_time,
                    base_pivot_confirmed_time=base_pivot_confirm_time,
                    base_open=finite_float(row.get("open")),
                    base_high=finite_float(row.get("high")),
                    base_low=finite_float(row.get("low")),
                    base_close=finite_float(row.get("close")),
                    audit_context_confirmed=audit_context_confirmed,
                    audit_context_confirm_lag_min=round(lag_min, 3) if math.isfinite(lag_min) else float("nan"),
                    audit_base_pivot_confirmed=audit_base_pivot_confirmed,
                    audit_context_pivot_confirmed=audit_context_pivot_confirmed,
                    audit_entry_after_signal=audit_entry_after_signal,
                    reason_text=reason,
                )
            )
    return rows


def load_timeframes(args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    paths = {
        "M1": args.m1_csv,
        "M5": args.m5_csv,
        "M15": args.m15_csv,
        "H1": args.h1_csv,
        "H4": args.h4_csv,
        "D1": args.d1_csv,
    }
    out: dict[str, pd.DataFrame] = {}
    for tf, p in paths.items():
        if not p:
            continue
        path = Path(p)
        if path.exists():
            raw = read_ohlc_csv(path)
            out[tf] = add_indicators(
                raw,
                tf,
                zigzag_depth=args.zigzag_depth,
                zigzag_deviation=args.zigzag_deviation,
                zigzag_deviation_mode=args.zigzag_deviation_mode,
                point_size=args.point_size,
                zigzag_backstep=args.zigzag_backstep,
            )
            print(f"loaded {tf}: rows={len(out[tf])} range={out[tf]['time'].min()} -> {out[tf]['time'].max()}")
    return out


def default_pairs(symbol: str) -> list[dict]:
    return DEFAULT_BTC_PAIRS if symbol.upper().startswith("BTC") else DEFAULT_GOLD_PAIRS


def write_summary(rows: list[CandidateRow], output_csv: Path, summary_json: Path) -> None:
    if rows:
        df = pd.DataFrame([asdict(r) for r in rows])
        summary = {
            "signals": int(len(df)),
            "output_csv": str(output_csv),
            "first_signal_time": str(df["signal_time"].min()),
            "last_signal_time": str(df["signal_time"].max()),
            "by_pair": df["pair_name"].value_counts().to_dict(),
            "by_rank": df["candidate_rank"].value_counts().to_dict(),
            "by_direction": df["direction"].value_counts().to_dict(),
            "by_pair_rank": {str(k): int(v) for k, v in df.groupby(["pair_name", "candidate_rank"]).size().items()},
            "audit": {
                "context_leak_violations": int((~df["audit_context_confirmed"]).sum()),
                "base_pivot_leak_violations": int((~df["audit_base_pivot_confirmed"]).sum()),
                "context_pivot_leak_violations": int((~df["audit_context_pivot_confirmed"]).sum()),
                "entry_timing_violations": int((~df["audit_entry_after_signal"]).sum()),
            },
        }
    else:
        summary = {"signals": 0, "output_csv": str(output_csv), "audit": {}}
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scan Mochipoyo-style multi-timeframe candidates with leak audits.")
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--m1-csv", default=None)
    p.add_argument("--m5-csv", default=None)
    p.add_argument("--m15-csv", default=None)
    p.add_argument("--h1-csv", default=None)
    p.add_argument("--h4-csv", default=None)
    p.add_argument("--d1-csv", default=None)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--summary-json", default=None)
    p.add_argument("--pairs-json", default=None, help="Optional JSON list of pair configs.")

    p.add_argument("--zigzag-depth", type=int, default=5)
    p.add_argument("--zigzag-deviation", type=float, default=3.0)
    p.add_argument("--zigzag-deviation-mode", choices=["price", "percent", "points"], default="price")
    p.add_argument("--zigzag-backstep", type=int, default=2)
    p.add_argument("--point-size", type=float, default=0.01)

    p.add_argument("--rci-zone", type=float, default=70.0)
    p.add_argument("--min-context-score", type=float, default=3.0)
    p.add_argument("--rank-a", type=float, default=8.0)
    p.add_argument("--rank-b", type=float, default=6.0)
    p.add_argument("--rank-c", type=float, default=4.5)
    p.add_argument("--min-context-atr", type=float, default=0.0)
    p.add_argument("--min-warmup-bars", type=int, default=80)
    p.add_argument("--require-divergence", action="store_true", help="Require context or base MACD divergence/hidden divergence.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print("scan_mochipoyo_multi_tf_candidates")
    print("confirmed-time rule: context_close_time <= base_close_time")
    print("zigzag confirmation rule: pivot_confirmed_time <= signal_close_time")
    print("entry rule: entry_time >= signal_close_time")

    tfs = load_timeframes(args)
    pairs = json.loads(Path(args.pairs_json).read_text(encoding="utf-8")) if args.pairs_json else default_pairs(args.symbol)
    all_rows: list[CandidateRow] = []

    for pair in pairs:
        context_tf = pair["context_tf"]
        base_tf = pair["base_tf"]
        if context_tf not in tfs or base_tf not in tfs:
            print(f"skip pair {pair['pair_name']}: missing tf context={context_tf in tfs}, base={base_tf in tfs}")
            continue
        joined = confirmed_join(tfs[base_tf], tfs[context_tf], base_tf, context_tf)
        rows = scan_pair(joined, pair, args)
        all_rows.extend(rows)
        print(f"pair {pair['pair_name']}: joined_rows={len(joined)} candidates={len(rows)}")

    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json) if args.summary_json else output_csv.with_suffix(".summary.json")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    df_out = pd.DataFrame([asdict(r) for r in all_rows])
    df_out.to_csv(output_csv, index=False, encoding="utf-8-sig")
    write_summary(all_rows, output_csv, summary_json)

    print(f"signals: {len(df_out)}")
    print(f"output_csv: {output_csv}")
    print(f"summary_json: {summary_json}")
    if len(df_out):
        context_viol = int((~df_out["audit_context_confirmed"]).sum())
        base_pivot_viol = int((~df_out["audit_base_pivot_confirmed"]).sum())
        context_pivot_viol = int((~df_out["audit_context_pivot_confirmed"]).sum())
        entry_viol = int((~df_out["audit_entry_after_signal"]).sum())
        print("by_pair:")
        print(df_out["pair_name"].value_counts().to_string())
        print("by_rank:")
        print(df_out["candidate_rank"].value_counts().to_string())
        print("by_direction:")
        print(df_out["direction"].value_counts().to_string())
        print("audit:")
        print(f"context_leak_violations: {context_viol}")
        print(f"base_pivot_leak_violations: {base_pivot_viol}")
        print(f"context_pivot_leak_violations: {context_pivot_viol}")
        print(f"entry_timing_violations: {entry_viol}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

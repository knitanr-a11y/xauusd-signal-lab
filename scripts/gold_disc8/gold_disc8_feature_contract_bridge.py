#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""DISC8 pre-entry feature contract bridge.

This module creates the AI-review feature names needed by the numeric tagger
from live/backtest OHLC data. It deliberately excludes post-entry/future fields
such as MFE/MAE.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from run_gold_disc8_live_decision_audit_forever_aligned import read_ohlc_csv, windows_long_path

FUTURE_FEATURE_BLACKLIST = {
    "m5_mfe_points",
    "m5_mae_points",
    "m1_mfe_points",
    "m1_mae_points",
    "m15_mfe_points",
    "m15_mae_points",
    "mfe_points",
    "mae_points",
    "max_favorable_excursion",
    "max_adverse_excursion",
}

REQUIRED_PRE_ENTRY_FEATURES = {
    "close_price",
    "h1_close_vs_ema20_atr",
    "h4_close_vs_ema20_atr",
    "h1_close_vs_ema50_atr",
    "h1_close_vs_ema200_atr",
    "m15_signal_candle_range_atr_ratio",
    "m15_ema20_distance_atr",
    "m15_signal_candle_body_ratio",
    "m15_macd_hist_delta_at_entry",
    "entry_position_in_m15_range_100_pct",
    "m15_signal_candle_range",
}


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    d = den.replace(0, pd.NA)
    return num / d


def add_indicators_contract(df: pd.DataFrame) -> pd.DataFrame:
    """Add base indicators and AI-review pre-entry aliases to one OHLC timeframe."""
    out = df.copy().sort_values("time").reset_index(drop=True)
    prev_close = out["close"].shift(1)
    tr = pd.concat([
        (out["high"] - out["low"]).abs(),
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=3).mean()
    for span in [20, 50, 200]:
        out[f"ema{span}"] = out["close"].ewm(span=span, adjust=False, min_periods=max(3, span // 3)).mean()
        out[f"dist_ema{span}_atr"] = _safe_div(out["close"] - out[f"ema{span}"], out["atr14"])
    ema12 = out["close"].ewm(span=12, adjust=False, min_periods=4).mean()
    ema26 = out["close"].ewm(span=26, adjust=False, min_periods=9).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False, min_periods=3).mean()
    out["macd_hist"] = macd - signal
    out["macd_hist_delta"] = out["macd_hist"] - out["macd_hist"].shift(1)
    for n in [4, 8, 16, 32, 48, 72, 96, 100]:
        hi = out["high"].rolling(n, min_periods=max(2, min(n, 5))).max().shift(1)
        lo = out["low"].rolling(n, min_periods=max(2, min(n, 5))).min().shift(1)
        out[f"donch_pos_{n}"] = _safe_div(out["close"] - lo, hi - lo)
        out[f"ret_{n}_atr"] = _safe_div(out["close"] - out["close"].shift(n), out["atr14"])
    out["close_price"] = out["close"]
    candle_range = (out["high"] - out["low"]).abs()
    out["m15_signal_candle_range"] = candle_range
    out["m15_signal_candle_range_atr_ratio"] = _safe_div(candle_range, out["atr14"])
    out["m15_signal_candle_body_ratio"] = _safe_div((out["close"] - out["open"]).abs(), candle_range)
    out["m15_ema20_distance_atr"] = out["dist_ema20_atr"]
    out["m15_macd_hist_delta_at_entry"] = out["macd_hist_delta"]
    hi100 = out["high"].rolling(100, min_periods=10).max().shift(1)
    lo100 = out["low"].rolling(100, min_periods=10).min().shift(1)
    out["entry_position_in_m15_range_100_pct"] = 100.0 * _safe_div(out["close"] - lo100, hi100 - lo100)
    return out


def with_context_close_time(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    delta = {"h1": pd.Timedelta(hours=1), "h4": pd.Timedelta(hours=4), "d1": pd.Timedelta(days=1)}[timeframe]
    out = df.copy()
    out[f"{timeframe}_close_time"] = out["time"] + delta
    return out


def prefix_context_contract(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    keep = [c for c in df.columns if c not in {"open", "high", "low", "volume"}]
    out = df[keep].copy()
    rename = {}
    for col in out.columns:
        if col == "time":
            rename[col] = f"{prefix}_open_time"
        elif col == f"{prefix}_close_time":
            rename[col] = f"{prefix}_close_time"
        elif not col.startswith(prefix + "_"):
            rename[col] = f"{prefix}_{col}"
    return out.rename(columns=rename)


def attach_context_contract(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    out = m15.copy().sort_values("time").reset_index(drop=True)
    for prefix, ctx in [("h1", h1), ("h4", h4), ("d1", d1)]:
        pref = prefix_context_contract(with_context_close_time(ctx, prefix), prefix).sort_values(f"{prefix}_close_time")
        out = pd.merge_asof(
            out.sort_values("time"), pref,
            left_on="time", right_on=f"{prefix}_close_time",
            direction="backward", allow_exact_matches=True,
        )
    return add_feature_contract_aliases(out.reset_index(drop=True))


def add_feature_contract_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Add AI-review feature aliases after HTF merge."""
    out = df.copy()
    if "close" in out.columns:
        out["close_price"] = out["close"]
    if "dist_ema20_atr" in out.columns:
        out["m15_ema20_distance_atr"] = out["dist_ema20_atr"]
    if "macd_hist_delta" in out.columns:
        out["m15_macd_hist_delta_at_entry"] = out["macd_hist_delta"]
    if {"high", "low"}.issubset(out.columns):
        rng = (out["high"] - out["low"]).abs()
        out["m15_signal_candle_range"] = rng
        if "atr14" in out.columns:
            out["m15_signal_candle_range_atr_ratio"] = _safe_div(rng, out["atr14"])
    if {"open", "close", "high", "low"}.issubset(out.columns):
        rng = (out["high"] - out["low"]).abs()
        out["m15_signal_candle_body_ratio"] = _safe_div((out["close"] - out["open"]).abs(), rng)
    if {"high", "low", "close"}.issubset(out.columns):
        hi100 = out["high"].rolling(100, min_periods=10).max().shift(1)
        lo100 = out["low"].rolling(100, min_periods=10).min().shift(1)
        out["entry_position_in_m15_range_100_pct"] = 100.0 * _safe_div(out["close"] - lo100, hi100 - lo100)
    for tf in ["h1", "h4", "d1"]:
        for span in [20, 50, 200]:
            dist = f"{tf}_dist_ema{span}_atr"
            alias = f"{tf}_close_vs_ema{span}_atr"
            close_col = f"{tf}_close"
            ema_col = f"{tf}_ema{span}"
            atr_col = f"{tf}_atr14"
            if dist in out.columns:
                out[alias] = out[dist]
            elif {close_col, ema_col, atr_col}.issubset(out.columns):
                out[alias] = _safe_div(out[close_col] - out[ema_col], out[atr_col])
    # Never synthesize future/post-entry features here.
    for col in FUTURE_FEATURE_BLACKLIST:
        if col in out.columns:
            out = out.drop(columns=[col])
    return out


def build_feature_frame_with_contract(csv_dir: Path, *, tail_m15: int = 60000, tail_h1: int = 30000, tail_h4: int = 10000, tail_d1: int = 3000) -> pd.DataFrame:
    m15 = add_indicators_contract(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=tail_m15))
    h1 = add_indicators_contract(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=tail_h1))
    h4 = add_indicators_contract(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=tail_h4))
    d1 = add_indicators_contract(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=tail_d1))
    return attach_context_contract(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)


def filter_pre_entry_rules(rules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for r in rules:
        feature = str(r.get("feature", "")).strip()
        if feature in FUTURE_FEATURE_BLACKLIST or any(token in feature.lower() for token in ["mfe", "mae", "post_entry", "after_entry"]):
            rr = dict(r)
            rr["excluded_reason"] = "FUTURE_OR_POST_ENTRY_FEATURE_BLACKLISTED"
            excluded.append(rr)
        else:
            kept.append(r)
    return kept, excluded

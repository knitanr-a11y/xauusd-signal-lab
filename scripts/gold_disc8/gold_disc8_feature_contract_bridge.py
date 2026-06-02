#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""DISC8 pre-entry feature contract bridge.

Creates AI-review numeric tagger feature names from live/backtest OHLC data
WITHOUT changing the existing live decision feature frame used for candidate
selection.

Important design rule:
- Candidate detection must use the existing live add_indicators/attach_context.
- This bridge only appends numeric-tagger alias features after that frame exists.
- Future/post-entry fields such as MFE/MAE are never synthesized.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from run_gold_disc8_live_decision_audit_forever_aligned import (
    add_indicators,
    attach_context,
    read_ohlc_csv,
)

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
    return num / den.replace(0, pd.NA)


def _atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=3).mean()


def _ema_distance_atr(df: pd.DataFrame, span: int) -> pd.Series:
    atr = _atr14(df)
    ema = df["close"].ewm(span=span, adjust=False, min_periods=max(3, span // 3)).mean()
    return _safe_div(df["close"] - ema, atr)


def _context_alias_frame(raw: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    delta = {"h1": pd.Timedelta(hours=1), "h4": pd.Timedelta(hours=4), "d1": pd.Timedelta(days=1)}[timeframe]
    out = raw.copy().sort_values("time").reset_index(drop=True)
    out[f"{timeframe}_bridge_close_time"] = out["time"] + delta
    for span in [20, 50, 200]:
        out[f"{timeframe}_close_vs_ema{span}_atr"] = _ema_distance_atr(out, span)
    keep = [f"{timeframe}_bridge_close_time"] + [f"{timeframe}_close_vs_ema{span}_atr" for span in [20, 50, 200]]
    return out[keep].copy().sort_values(f"{timeframe}_bridge_close_time")


def _merge_context_aliases(frame: pd.DataFrame, raw_ctx: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    alias = _context_alias_frame(raw_ctx, timeframe)
    close_col = f"{timeframe}_bridge_close_time"
    out = pd.merge_asof(
        frame.sort_values("time"),
        alias,
        left_on="time",
        right_on=close_col,
        direction="backward",
        allow_exact_matches=True,
    )
    if close_col in out.columns:
        out = out.drop(columns=[close_col])
    # Prefer existing live dist aliases for 50/200 when present. This preserves live calculations.
    for span in [50, 200]:
        live_col = f"{timeframe}_dist_ema{span}_atr"
        alias_col = f"{timeframe}_close_vs_ema{span}_atr"
        if live_col in out.columns:
            out[alias_col] = out[live_col]
    return out.reset_index(drop=True)


def add_feature_contract_aliases(df: pd.DataFrame, *, raw_m15: pd.DataFrame | None = None) -> pd.DataFrame:
    """Append AI-review feature aliases without altering existing live feature columns."""
    out = df.copy()
    if "close" in out.columns:
        out["close_price"] = out["close"]
    if raw_m15 is not None and not raw_m15.empty:
        m15 = raw_m15.copy().sort_values("time").reset_index(drop=True)
        atr = _atr14(m15)
        ema20 = m15["close"].ewm(span=20, adjust=False, min_periods=max(3, 20 // 3)).mean()
        macd_base = add_indicators(m15)
        alias = pd.DataFrame({
            "time": m15["time"],
            "m15_ema20_distance_atr": _safe_div(m15["close"] - ema20, atr),
            "m15_macd_hist_delta_at_entry": macd_base["macd_hist"] - macd_base["macd_hist"].shift(1),
            "m15_signal_candle_range": (m15["high"] - m15["low"]).abs(),
            "m15_signal_candle_body_ratio": _safe_div((m15["close"] - m15["open"]).abs(), (m15["high"] - m15["low"]).abs()),
            "m15_signal_candle_range_atr_ratio": _safe_div((m15["high"] - m15["low"]).abs(), atr),
            "entry_position_in_m15_range_100_pct": 100.0 * _safe_div(
                m15["close"] - m15["low"].rolling(100, min_periods=10).min().shift(1),
                m15["high"].rolling(100, min_periods=10).max().shift(1) - m15["low"].rolling(100, min_periods=10).min().shift(1),
            ),
        }).sort_values("time")
        out = pd.merge_asof(out.sort_values("time"), alias, on="time", direction="backward", allow_exact_matches=True)
    else:
        if "dist_ema20_atr" in out.columns:
            out["m15_ema20_distance_atr"] = out["dist_ema20_atr"]
        if "macd_hist" in out.columns:
            out["m15_macd_hist_delta_at_entry"] = out["macd_hist"] - out["macd_hist"].shift(1)
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
    for col in FUTURE_FEATURE_BLACKLIST:
        if col in out.columns:
            out = out.drop(columns=[col])
    return out.reset_index(drop=True)


def build_feature_frame_with_contract(csv_dir: Path, *, tail_m15: int = 60000, tail_h1: int = 30000, tail_h4: int = 10000, tail_d1: int = 3000) -> pd.DataFrame:
    """Build live-compatible frame, then append numeric-tagger feature aliases.

    This must preserve candidate detection parity with the existing live audit path.
    """
    raw_m15 = read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=tail_m15)
    raw_h1 = read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=tail_h1)
    raw_h4 = read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=tail_h4)
    raw_d1 = read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=tail_d1)

    # Existing live feature path. Do not replace this with contract-specific indicators.
    m15 = add_indicators(raw_m15)
    h1 = add_indicators(raw_h1)
    h4 = add_indicators(raw_h4)
    d1 = add_indicators(raw_d1)
    frame = attach_context(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)

    # Append missing AI-review aliases only after the live-compatible frame is built.
    frame = add_feature_contract_aliases(frame, raw_m15=raw_m15)
    for tf, raw in [("h1", raw_h1), ("h4", raw_h4), ("d1", raw_d1)]:
        frame = _merge_context_aliases(frame, raw, tf)
    return frame.sort_values("time").reset_index(drop=True)


def filter_pre_entry_rules(rules: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    excluded: list[dict] = []
    for r in rules:
        feature = str(r.get("feature", "")).strip()
        if feature in FUTURE_FEATURE_BLACKLIST or any(token in feature.lower() for token in ["mfe", "mae", "post_entry", "after_entry"]):
            rr = dict(r)
            rr["excluded_reason"] = "FUTURE_OR_POST_ENTRY_FEATURE_BLACKLISTED"
            excluded.append(rr)
        else:
            kept.append(r)
    return kept, excluded

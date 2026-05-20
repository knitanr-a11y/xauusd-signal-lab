#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared official runtime helpers for BTC strict 5.

Official default filter variant:
    buy_h4_context_conservative_v1

This module centralizes the filtered signal detection path so backtest, preview,
Discord, and guarded demo wrappers can avoid drift.  Baseline remains available
only by explicitly passing --filter-variant baseline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from btc_strict_5_filter_variants import (
    BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
    apply_filter_variant,
    describe_filter_variant,
)
from btc_strict_5_signal_specs import DEFAULT_BROKER_SYMBOL, DEFAULT_SYMBOL, get_signal_specs
from run_btc_strict_5_backtest_from_csv import (
    add_indicators,
    detect_signals,
    join_confirmed_context,
    read_ohlc_csv,
)
from run_btc_strict_5_preview_from_csv import build_m15_next_open_lookup, build_preview_rows


def read_ohlc_csv_tail(path: str | Path, tail_bars: int = 0) -> pd.DataFrame:
    df = read_ohlc_csv(path)
    if tail_bars and int(tail_bars) > 0:
        return df.tail(int(tail_bars)).reset_index(drop=True)
    return df


def build_context_from_csvs(
    *,
    m15_csv: str | Path,
    h1_csv: str | Path,
    h4_csv: str | Path,
    tail_m15: int = 0,
    tail_h1: int = 0,
    tail_h4: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m15 = add_indicators(read_ohlc_csv_tail(m15_csv, tail_m15), include_donchian=True)
    h1 = add_indicators(read_ohlc_csv_tail(h1_csv, tail_h1))
    h4 = add_indicators(read_ohlc_csv_tail(h4_csv, tail_h4))
    ctx = join_confirmed_context(m15, h1, h4)
    return m15, h1, h4, ctx


def detect_filtered_signals(
    ctx: pd.DataFrame,
    *,
    filter_variant: str = BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = detect_signals(ctx, get_signal_specs())
    kept, excluded = apply_filter_variant(raw, ctx, filter_variant=filter_variant)
    return raw, kept, excluded


def build_filtered_preview(
    *,
    m15: pd.DataFrame,
    ctx: pd.DataFrame,
    filter_variant: str = BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
    scan_recent_bars: int = 500,
    max_signal_age_minutes: int = 0,
    latest_only: bool = False,
    broker_symbol: str = DEFAULT_BROKER_SYMBOL,
    symbol: str = DEFAULT_SYMBOL,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    raw, kept, excluded = detect_filtered_signals(ctx, filter_variant=filter_variant)
    signals = kept.copy()
    if scan_recent_bars and int(scan_recent_bars) > 0 and not ctx.empty and not signals.empty:
        cutoff_idx = max(0, len(ctx) - int(scan_recent_bars))
        cutoff_time = pd.Timestamp(ctx.iloc[cutoff_idx]["time"])
        signals = signals[pd.to_datetime(signals["signal_time"]) >= cutoff_time].copy()
    if max_signal_age_minutes and int(max_signal_age_minutes) > 0 and not ctx.empty and not signals.empty:
        end_close_time = pd.Timestamp(ctx.iloc[-1]["base_close_time"])
        start_time = end_close_time - pd.Timedelta(minutes=int(max_signal_age_minutes))
        signals = signals[pd.to_datetime(signals["base_close_time"]) >= start_time].copy()
    if latest_only and not signals.empty:
        signals = signals.sort_values(["signal_time", "strategy_id"]).tail(1).copy()
    preview = build_preview_rows(
        signals=signals,
        ctx=ctx,
        m15_next_open_lookup=build_m15_next_open_lookup(m15),
        broker_symbol=broker_symbol,
        symbol=symbol,
    )
    meta = {
        "filter_variant": filter_variant,
        "filter_variant_description": describe_filter_variant(filter_variant),
        "raw_signals_before_filter": int(len(raw)),
        "signals_excluded_by_filter": int(len(excluded)),
        "signals_after_filter_before_recent_window": int(len(kept)),
        "signals_after_recent_filters": int(len(signals)),
        "preview_rows": int(len(preview)),
        "d1_used": False,
    }
    return preview, raw, excluded, meta

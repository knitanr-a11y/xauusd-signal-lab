#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Fixed wrapper for GOLD specialist 8 validation backtest.

Why this wrapper exists:
- The first validation backtest implementation computed H1 Donchian columns, but
  did not merge those H1 Donchian columns into the M15 decision context.
- As a result, the Donchian-based candidates could not fire, and the validation
  outcome CSV could be dominated by only the non-Donchian strategies.

This wrapper imports the original implementation, replaces make_htf_context with a
fixed version that carries higher-timeframe Donchian columns, then runs the same
main() entry point.  No MT5 order send, no Discord send, no AI call.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
ORIGINAL = SCRIPT_DIR / "run_gold_specialist_8_validation_backtest.py"

spec = importlib.util.spec_from_file_location("gold_specialist_8_validation_backtest_original", ORIGINAL)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load original validation backtest script: {ORIGINAL}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_htf_context_fixed(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    """Merge confirmed H1/H4/D1 context into M15 without dropping Donchian columns.

    H1 Donchian columns are required by these strategies:
    - BUY_H1_DONCH72_ADX18_STRUCT_RR2_MIN50_CAP220
    - BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220
    - SELL_H1_DONCH36_ADX10_TP150_SL75_JST20_22
    - SELL_H1_DONCH72_ADX10_TP50_SL25_JST18_22
    - BUY_H1_DONCH20_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST01_05

    The merge remains as-of backward on close_time, so the HTF bar used is always
    close_time <= M15 signal close_time.
    """
    base = m15.copy().sort_values("close_time")
    htf_items: list[tuple[str, pd.DataFrame]] = [("h1", h1), ("h4", h4), ("d1", d1)]
    for tf_name, tf_df in htf_items:
        if tf_df.empty:
            continue
        wanted = [
            "close_time",
            "open",
            "high",
            "low",
            "close",
            "ema20",
            "ema34",
            "ema50",
            "ema200",
            "atr14",
            "adx14",
            "rsi14",
            "cci20",
            "donch_high_20",
            "donch_low_20",
            "donch_high_36",
            "donch_low_36",
            "donch_high_72",
            "donch_low_72",
        ]
        keep_cols = [c for c in wanted if c in tf_df.columns]
        keep = tf_df[keep_cols].copy().sort_values("close_time")
        keep[f"{tf_name}_source_close_time"] = keep["close_time"]
        rename_map: dict[str, str] = {}
        for c in keep.columns:
            if c == "close_time" or c == f"{tf_name}_source_close_time":
                continue
            rename_map[c] = f"{tf_name}_{c}"
        keep = keep.rename(columns=rename_map)
        base = pd.merge_asof(
            base,
            keep,
            left_on="close_time",
            right_on="close_time",
            direction="backward",
        )
    return base.sort_values("time").reset_index(drop=True)


mod.make_htf_context = make_htf_context_fixed

if __name__ == "__main__":
    raise SystemExit(mod.main())

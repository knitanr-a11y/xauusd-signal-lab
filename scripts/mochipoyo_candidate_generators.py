#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused candidate generators for the Mochipoyo minimal scanner.

This module deliberately reuses the existing audited indicator/scoring functions
from scan_mochipoyo_multi_tf_candidates.py, but does not run that full scanner
script or scan every pair.  Callers must pass the already-selected pair and the
already-read base/context DataFrames.

Current scope:
- GOLD_H4_M5_SCALP
- GOLD_H4_M15_DAYTRADE

The generator returns candidate EVENTS, not raw persistent states, by applying
the same event filter defaults used by filter_mochipoyo_candidate_events.py.
Allowed-slice filtering is applied after normalization, so pair configs decide
which ranks/directions survive.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any, Mapping

import pandas as pd

try:  # Package import from repository root.
    from scripts.filter_mochipoyo_candidate_events import apply_cooldown, apply_daily_cap, has_any_divergence, has_granville, rank_ok
    from scripts.mochipoyo_candidate_normalizer import filter_allowed_slices as filter_normalized_allowed_slices
    from scripts.mochipoyo_candidate_normalizer import normalize_minimal_candidates, split_risk_ok_ng
    from scripts.scan_mochipoyo_multi_tf_candidates import add_indicators, confirmed_join, scan_pair
except ModuleNotFoundError:  # Direct execution/import from scripts/.
    from filter_mochipoyo_candidate_events import apply_cooldown, apply_daily_cap, has_any_divergence, has_granville, rank_ok  # type: ignore
    from mochipoyo_candidate_normalizer import filter_allowed_slices as filter_normalized_allowed_slices  # type: ignore
    from mochipoyo_candidate_normalizer import normalize_minimal_candidates, split_risk_ok_ng  # type: ignore
    from scan_mochipoyo_multi_tf_candidates import add_indicators, confirmed_join, scan_pair  # type: ignore

SUPPORTED_GENERATOR_PAIRS = {
    "GOLD_H4_M5_SCALP",
    "GOLD_H4_M15_DAYTRADE",
}


def default_scan_args(symbol: str) -> argparse.Namespace:
    """Return defaults matching scan_mochipoyo_multi_tf_candidates.py."""
    return argparse.Namespace(
        symbol=symbol,
        zigzag_depth=5,
        zigzag_deviation=3.0,
        zigzag_deviation_mode="price",
        zigzag_backstep=2,
        point_size=0.01,
        rci_zone=70.0,
        min_context_score=3.0,
        rank_a=8.0,
        rank_b=6.0,
        rank_c=4.5,
        min_context_atr=0.0,
        min_warmup_bars=80,
        require_divergence=True,
    )


def default_event_filter_args() -> argparse.Namespace:
    """Return defaults matching filter_mochipoyo_candidate_events.py."""
    return argparse.Namespace(
        min_rank="B",
        require_any_divergence=True,
        require_granville=True,
        cooldown_minutes_default=240,
        max_per_day_per_pair_direction=6,
    )


def build_pair_dict(cfg: Mapping[str, Any]) -> dict[str, str]:
    return {
        "pair_name": str(cfg["pair_name"]),
        "style": "scalp" if "SCALP" in str(cfg["pair_name"]).upper() else "daytrade",
        "context_tf": next(iter(dict(cfg.get("context", {})).keys())),
        "base_tf": str(cfg["base_timeframe"]),
    }


def add_pair_indicators(base_df: pd.DataFrame, context_df: pd.DataFrame, cfg: Mapping[str, Any], scan_args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair = build_pair_dict(cfg)
    base_ind = add_indicators(
        base_df,
        pair["base_tf"],
        zigzag_depth=scan_args.zigzag_depth,
        zigzag_deviation=scan_args.zigzag_deviation,
        zigzag_deviation_mode=scan_args.zigzag_deviation_mode,
        point_size=scan_args.point_size,
        zigzag_backstep=scan_args.zigzag_backstep,
    )
    context_ind = add_indicators(
        context_df,
        pair["context_tf"],
        zigzag_depth=scan_args.zigzag_depth,
        zigzag_deviation=scan_args.zigzag_deviation,
        zigzag_deviation_mode=scan_args.zigzag_deviation_mode,
        point_size=scan_args.point_size,
        zigzag_backstep=scan_args.zigzag_backstep,
    )
    return base_ind, context_ind


def candidate_states_for_pair(base_df: pd.DataFrame, context_df: pd.DataFrame, cfg: Mapping[str, Any], *, scan_args: argparse.Namespace | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate broad candidate state rows for one supported pair.

    Returns:
        states_df, joined_df
    """
    pair_name = str(cfg["pair_name"])
    if pair_name not in SUPPORTED_GENERATOR_PAIRS:
        return pd.DataFrame(), pd.DataFrame()
    scan_args = scan_args or default_scan_args(str(cfg.get("symbol", "GOLD")))
    pair = build_pair_dict(cfg)
    base_ind, context_ind = add_pair_indicators(base_df, context_df, cfg, scan_args)
    joined = confirmed_join(base_ind, context_ind, pair["base_tf"], pair["context_tf"])
    rows = scan_pair(joined, pair, scan_args)
    states_df = pd.DataFrame([asdict(row) for row in rows])
    return states_df, joined


def filter_candidate_events(states_df: pd.DataFrame, *, event_args: argparse.Namespace | None = None) -> pd.DataFrame:
    """Apply event filtering equivalent to filter_mochipoyo_candidate_events.py defaults."""
    event_args = event_args or default_event_filter_args()
    if states_df.empty:
        return states_df.copy()
    df = states_df.copy()
    df["signal_close_time"] = pd.to_datetime(df["signal_close_time"], errors="coerce")
    df = df.dropna(subset=["signal_close_time"])
    df = df[df["candidate_rank"].map(lambda x: rank_ok(str(x), event_args.min_rank))]
    if event_args.require_any_divergence:
        df = df[df.apply(has_any_divergence, axis=1)]
    if event_args.require_granville:
        df = df[df.apply(has_granville, axis=1)]
    if df.empty:
        return df.reset_index(drop=True)
    df = df.sort_values(["signal_close_time", "pair_name", "direction", "total_score"], ascending=[True, True, True, False]).reset_index(drop=True)
    df = apply_cooldown(df, event_args.cooldown_minutes_default)
    df = apply_daily_cap(df, event_args.max_per_day_per_pair_direction)
    return df.reset_index(drop=True)


def add_selected_slice(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not out.empty and {"pair_name", "candidate_rank", "direction"}.issubset(out.columns):
        out["selected_slice"] = out["pair_name"].astype(str) + "|" + out["candidate_rank"].astype(str) + "|" + out["direction"].astype(str)
    return out


def generate_pair_events(
    base_df: pd.DataFrame,
    context_df: pd.DataFrame,
    cfg: Mapping[str, Any],
    *,
    allowed_slices: list[dict[str, str]],
    scan_args: argparse.Namespace | None = None,
    event_args: argparse.Namespace | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate and normalize candidate events for one supported pair."""
    states_df, joined_df = candidate_states_for_pair(base_df, context_df, cfg, scan_args=scan_args)
    events_df = add_selected_slice(filter_candidate_events(states_df, event_args=event_args))
    normalized_df = normalize_minimal_candidates(events_df) if not events_df.empty else normalize_minimal_candidates(pd.DataFrame())
    if not normalized_df.empty:
        normalized_df = filter_normalized_allowed_slices(normalized_df, allowed_slices)
    risk_ok_df, risk_ng_df = split_risk_ok_ng(normalized_df)
    return {
        "joined_df": joined_df,
        "raw_states_df": states_df,
        "raw_candidates_df": events_df,
        "normalized_candidates_df": normalized_df,
        "risk_ok_candidates_df": risk_ok_df,
        "risk_ng_candidates_df": risk_ng_df,
    }


__all__ = [
    "SUPPORTED_GENERATOR_PAIRS",
    "add_pair_indicators",
    "add_selected_slice",
    "build_pair_dict",
    "candidate_states_for_pair",
    "default_event_filter_args",
    "default_scan_args",
    "filter_candidate_events",
    "generate_pair_events",
]

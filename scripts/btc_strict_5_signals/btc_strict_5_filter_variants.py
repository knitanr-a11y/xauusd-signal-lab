#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filter variants for BTC strict 5 signals.

The default official BTC strict-5 operating variant is
``buy_h4_context_conservative_v1``.

Why this module exists:
- backtest / preview / Discord / guarded demo must use the same filter logic
- baseline must remain available for research comparison
- filters must be deterministic numeric conditions, not AI tags
- D1 is intentionally not used

Current official variant:
- BUY CCI: exclude when confirmed H4 close is materially below H4 EMA50
- BUY RSI40: exclude when confirmed H4 close is not sufficiently above H4 EMA20

These thresholds came from BTC strict-5 full backtest AI-review diagnostics and
were then confirmed in a deterministic variant backtest.  They are fixed
constants and must not be recomputed from the backtest distribution at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

FilterOp = Literal["<=", ">="]

BTC_STRICT_5_BASELINE_VARIANT = "baseline"
BTC_STRICT_5_DEFAULT_FILTER_VARIANT = "buy_h4_context_conservative_v1"

BTC_BUY_CCI_ID = "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0"
BTC_BUY_RSI40_ID = "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0"


@dataclass(frozen=True)
class BtcStrict5FilterRule:
    filter_id: str
    strategy_id: str
    feature_name: str
    op: FilterOp
    threshold: float
    source_tag: str
    source_diagnostic_grade: str
    notes: str


def available_filter_variants() -> list[str]:
    return [
        BTC_STRICT_5_BASELINE_VARIANT,
        BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
    ]


def get_filter_rules(filter_variant: str) -> list[BtcStrict5FilterRule]:
    variant = (filter_variant or BTC_STRICT_5_DEFAULT_FILTER_VARIANT).strip()
    if variant == BTC_STRICT_5_BASELINE_VARIANT:
        return []
    if variant == BTC_STRICT_5_DEFAULT_FILTER_VARIANT:
        return [
            BtcStrict5FilterRule(
                filter_id="BUY_CCI_H4_EMA50_ATR_LE_NEG02321258027",
                strategy_id=BTC_BUY_CCI_ID,
                feature_name="h4_close_vs_ema50_atr",
                op="<=",
                threshold=-0.2321258027,
                source_tag="against_h4_context",
                source_diagnostic_grade="A_NUMERIC_FILTER_CANDIDATE",
                notes="Exclude BUY CCI when confirmed H4 close is materially below H4 EMA50.",
            ),
            BtcStrict5FilterRule(
                filter_id="BUY_RSI40_H4_EMA20_ATR_LE_02718471001",
                strategy_id=BTC_BUY_RSI40_ID,
                feature_name="h4_close_vs_ema20_atr",
                op="<=",
                threshold=0.2718471001,
                source_tag="against_h4_context",
                source_diagnostic_grade="A_NUMERIC_FILTER_CANDIDATE",
                notes="Exclude BUY RSI40 when confirmed H4 close is not sufficiently above H4 EMA20.",
            ),
        ]
    raise ValueError(f"unknown BTC strict 5 filter_variant={variant!r}; available={available_filter_variants()}")


def h4_close_vs_ema_atr(ctx_row: pd.Series, ema_col: str) -> float:
    close = pd.to_numeric(ctx_row.get("h4_close"), errors="coerce")
    ema = pd.to_numeric(ctx_row.get(ema_col), errors="coerce")
    atr = pd.to_numeric(ctx_row.get("h4_atr14"), errors="coerce")
    if pd.isna(close) or pd.isna(ema) or pd.isna(atr) or abs(float(atr)) <= 1e-12:
        return np.nan
    return (float(close) - float(ema)) / abs(float(atr))


def compute_filter_feature(ctx_row: pd.Series, feature_name: str) -> float:
    if feature_name == "h4_close_vs_ema20_atr":
        return h4_close_vs_ema_atr(ctx_row, "h4_ema20")
    if feature_name == "h4_close_vs_ema50_atr":
        return h4_close_vs_ema_atr(ctx_row, "h4_ema50")
    raise KeyError(f"unsupported BTC strict 5 filter feature: {feature_name}")


def rule_matches(value: float, op: FilterOp, threshold: float) -> bool:
    if np.isnan(value):
        return False
    if op == "<=":
        return float(value) <= float(threshold)
    if op == ">=":
        return float(value) >= float(threshold)
    raise ValueError(f"unsupported op: {op}")


def apply_filter_variant(
    signals: pd.DataFrame,
    ctx: pd.DataFrame,
    *,
    filter_variant: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (kept_signals, excluded_signals) after deterministic filters.

    The returned DataFrames include audit columns:
    - filter_variant
    - filter_variant_excluded
    - filter_variant_excluded_by
    - filter_feature_* for used numeric features
    """
    variant = (filter_variant or BTC_STRICT_5_DEFAULT_FILTER_VARIANT).strip()
    rules = get_filter_rules(variant)
    if signals.empty:
        kept = signals.copy()
        kept["filter_variant"] = variant
        kept["filter_variant_excluded"] = False
        kept["filter_variant_excluded_by"] = ""
        return kept, pd.DataFrame()
    if not rules:
        kept = signals.copy()
        kept["filter_variant"] = variant
        kept["filter_variant_excluded"] = False
        kept["filter_variant_excluded_by"] = ""
        return kept, pd.DataFrame()

    ctx_by_index = {int(i): row for i, row in ctx.iterrows()}
    rules_by_strategy: dict[str, list[BtcStrict5FilterRule]] = {}
    for rule in rules:
        rules_by_strategy.setdefault(rule.strategy_id, []).append(rule)

    kept_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    for _, sig in signals.iterrows():
        out = sig.to_dict()
        out["filter_variant"] = variant
        out["filter_variant_excluded"] = False
        out["filter_variant_excluded_by"] = ""
        strategy_id = str(sig.get("strategy_id"))
        ctx_row = ctx_by_index.get(int(sig.get("source_index", -1)))
        reasons: list[str] = []
        if ctx_row is not None:
            for rule in rules_by_strategy.get(strategy_id, []):
                value = compute_filter_feature(ctx_row, rule.feature_name)
                out[f"filter_feature_{rule.feature_name}"] = value
                if rule_matches(value, rule.op, rule.threshold):
                    reasons.append(
                        f"{rule.filter_id}:{rule.feature_name} {rule.op} {rule.threshold} value={value}"
                    )
        if reasons:
            out["filter_variant_excluded"] = True
            out["filter_variant_excluded_by"] = "; ".join(reasons)
            excluded_rows.append(out)
        else:
            kept_rows.append(out)

    kept = pd.DataFrame(kept_rows)
    excluded = pd.DataFrame(excluded_rows)
    if not kept.empty:
        kept = kept.sort_values(["entry_time", "strategy_id"]).reset_index(drop=True)
    if not excluded.empty:
        excluded = excluded.sort_values(["entry_time", "strategy_id"]).reset_index(drop=True)
    return kept, excluded


def describe_filter_variant(filter_variant: str | None = None) -> dict[str, Any]:
    variant = (filter_variant or BTC_STRICT_5_DEFAULT_FILTER_VARIANT).strip()
    rules = get_filter_rules(variant)
    return {
        "filter_variant": variant,
        "is_default_official_variant": variant == BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "available_filter_variants": available_filter_variants(),
        "rules": [rule.__dict__ for rule in rules],
        "d1_used": False,
    }


if __name__ == "__main__":
    for v in available_filter_variants():
        print(describe_filter_variant(v))

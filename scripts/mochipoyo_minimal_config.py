#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared configuration for the Mochipoyo live notification minimal scanner.

This module intentionally contains no scanner logic.  It only centralizes the
pair universe, CSV filename mapping, timeframe close-time definitions, default
allowed slices, and small helper functions used by:

- compare_mochipoyo_full_strict_vs_minimal.py
- mochipoyo_minimal_scanner.py
- run_mochipoyo_live_notify_loop_minimal.py

Important design rule:
    allowed_slices -> required pairs -> scan required pairs only.

Do not use this module to run a broad full scan and then filter afterwards.

Future auto-trade bridge rule:
    This notification system remains Python-side decision logic.  If/when auto
    trading is enabled, Python should write an order_intent file and a single
    MQL5 Bridge EA should execute it inside MT5.  Therefore pair configs include
    mt5_symbol / auto_trade_enabled placeholders now, but auto_trade_enabled is
    intentionally False for every pair at this stage.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

TIMEFRAME_MINUTES: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

CSV_KEYS: dict[str, str] = {
    "gold_m5": "goldsharp_m5.csv",
    "gold_m15": "goldsharp_m15.csv",
    "gold_h1": "goldsharp_h1.csv",
    "gold_h4": "goldsharp_h4.csv",
    "gold_d1": "goldsharp_d1.csv",
    "btc_m5": "btcusdsharp_m5.csv",
    "btc_m15": "btcusdsharp_m15.csv",
    "btc_h1": "btcusdsharp_h1.csv",
    "btc_h4": "btcusdsharp_h4.csv",
}

# Broker-facing MT5 symbols are intentionally separated from internal symbols.
# Adjust these when moving between brokers/accounts (for example XAUUSD vs GOLD#).
DEFAULT_MT5_SYMBOL_BY_SYMBOL: dict[str, str] = {
    "GOLD": "GOLD#",
    "BTC": "BTCUSD#",
}

DEFAULT_TAIL_BARS: dict[str, int] = {
    "M1": 12000,
    "M5": 6000,
    "M15": 5000,
    "H1": 1500,
    "H4": 1500,
    "D1": 800,
}

DEFAULT_ALLOWED_SLICES: list[dict[str, str]] = [
    {"pair_name": "GOLD_H4_M5_SCALP", "candidate_rank": "A", "direction": "SELL"},
    {"pair_name": "GOLD_H4_M5_SCALP", "candidate_rank": "B", "direction": "SELL"},
    {"pair_name": "GOLD_H4_M15_DAYTRADE", "candidate_rank": "B", "direction": "BUY"},
    {"pair_name": "GOLD_H4_M15_DAYTRADE", "candidate_rank": "B", "direction": "SELL"},
    {"pair_name": "GOLD_D1_H1_DAYTRADE", "candidate_rank": "A", "direction": "BUY"},
    {"pair_name": "GOLD_D1_H1_DAYTRADE", "candidate_rank": "B", "direction": "BUY"},
    {"pair_name": "BTC_H4_M15_DAYTRADE", "candidate_rank": "A", "direction": "BUY"},
    {"pair_name": "BTC_H4_M15_DAYTRADE", "candidate_rank": "A", "direction": "SELL"},
]

PAIR_CONFIGS: dict[str, dict[str, Any]] = {
    "GOLD_H4_M5_SCALP": {
        "pair_name": "GOLD_H4_M5_SCALP",
        "symbol": "GOLD",
        "mt5_symbol": "GOLD#",
        "auto_trade_enabled": False,
        "base_timeframe": "M5",
        "trigger_timeframe": "M5",
        "base_csv_key": "gold_m5",
        "context": {"H4": "gold_h4"},
        "allowed_slices": [
            {"candidate_rank": "A", "direction": "SELL"},
            {"candidate_rank": "B", "direction": "SELL"},
        ],
        "tail_bars": {"M5": 6000, "H4": 1500},
        "price_digits": 2,
        "requires_spread": False,
    },
    "GOLD_H4_M15_DAYTRADE": {
        "pair_name": "GOLD_H4_M15_DAYTRADE",
        "symbol": "GOLD",
        "mt5_symbol": "GOLD#",
        "auto_trade_enabled": False,
        "base_timeframe": "M15",
        "trigger_timeframe": "M15",
        "base_csv_key": "gold_m15",
        "context": {"H4": "gold_h4"},
        "allowed_slices": [
            {"candidate_rank": "B", "direction": "BUY"},
            {"candidate_rank": "B", "direction": "SELL"},
        ],
        "tail_bars": {"M15": 5000, "H4": 1500},
        "price_digits": 2,
        "requires_spread": False,
    },
    "GOLD_D1_H1_DAYTRADE": {
        "pair_name": "GOLD_D1_H1_DAYTRADE",
        "symbol": "GOLD",
        "mt5_symbol": "GOLD#",
        "auto_trade_enabled": False,
        "base_timeframe": "H1",
        "trigger_timeframe": "H1",
        "base_csv_key": "gold_h1",
        "context": {"D1": "gold_d1"},
        "allowed_slices": [
            {"candidate_rank": "A", "direction": "BUY"},
            {"candidate_rank": "B", "direction": "BUY"},
        ],
        "tail_bars": {"H1": 1500, "D1": 800},
        "price_digits": 2,
        "requires_spread": False,
    },
    "BTC_H4_M15_DAYTRADE": {
        "pair_name": "BTC_H4_M15_DAYTRADE",
        "symbol": "BTC",
        "mt5_symbol": "BTCUSD#",
        "auto_trade_enabled": False,
        "base_timeframe": "M15",
        "trigger_timeframe": "M15",
        "base_csv_key": "btc_m15",
        "context": {"H4": "btc_h4"},
        "allowed_slices": [
            {"candidate_rank": "A", "direction": "BUY"},
            {"candidate_rank": "A", "direction": "SELL"},
        ],
        "tail_bars": {"M15": 5000, "H4": 1500},
        "price_digits": 2,
        "requires_spread": True,
        "spread_source_csv_key": "btc_m15",
    },
}


class MinimalConfigError(ValueError):
    """Raised when minimal scanner configuration is invalid."""


def normalize_pair_name(pair_name: object) -> str:
    value = str(pair_name or "").strip().upper()
    if not value:
        raise MinimalConfigError("pair_name is required")
    return value


def normalize_symbol(symbol: object) -> str:
    value = str(symbol or "").strip().upper()
    if not value:
        raise MinimalConfigError("symbol is required")
    return value


def normalize_candidate_rank(candidate_rank: object) -> str:
    value = str(candidate_rank or "").strip().upper()
    if not value:
        raise MinimalConfigError("candidate_rank is required")
    return value


def normalize_direction(direction: object) -> str:
    value = str(direction or "").strip().upper()
    if value not in {"BUY", "SELL"}:
        raise MinimalConfigError(f"direction must be BUY or SELL, got {direction!r}")
    return value


def normalize_mt5_symbol(mt5_symbol: object) -> str:
    value = str(mt5_symbol or "").strip()
    if not value:
        raise MinimalConfigError("mt5_symbol is required")
    return value


def normalize_allowed_slice(row: Mapping[str, Any] | str) -> dict[str, str]:
    """Normalize one allowed slice.

    Accepted formats:
        {"pair_name": "GOLD_H4_M5_SCALP", "candidate_rank": "A", "direction": "SELL"}
        "GOLD_H4_M5_SCALP|A|SELL"
    """
    if isinstance(row, str):
        parts = [part.strip() for part in row.split("|")]
        if len(parts) != 3:
            raise MinimalConfigError(f"allowed slice string must be pair|rank|direction: {row!r}")
        pair_name, candidate_rank, direction = parts
    else:
        pair_name = row.get("pair_name")
        candidate_rank = row.get("candidate_rank")
        direction = row.get("direction")
    return {
        "pair_name": normalize_pair_name(pair_name),
        "candidate_rank": normalize_candidate_rank(candidate_rank),
        "direction": normalize_direction(direction),
    }


def normalize_allowed_slices(rows: Iterable[Mapping[str, Any] | str] | None) -> list[dict[str, str]]:
    if rows is None:
        rows = DEFAULT_ALLOWED_SLICES
    return [normalize_allowed_slice(row) for row in rows]


def allowed_slice_to_string(row: Mapping[str, Any]) -> str:
    normalized = normalize_allowed_slice(row)
    return "|".join([normalized["pair_name"], normalized["candidate_rank"], normalized["direction"]])


def get_required_pair_names(allowed_slices: Iterable[Mapping[str, Any] | str] | None = None) -> list[str]:
    normalized = normalize_allowed_slices(allowed_slices)
    seen: set[str] = set()
    ordered: list[str] = []
    for row in normalized:
        pair_name = row["pair_name"]
        if pair_name not in PAIR_CONFIGS:
            raise MinimalConfigError(f"Unknown pair_name in allowed_slices: {pair_name}")
        if pair_name not in seen:
            ordered.append(pair_name)
            seen.add(pair_name)
    return ordered


def filter_allowed_slices_for_pair(
    allowed_slices: Iterable[Mapping[str, Any] | str] | None,
    pair_name: str,
) -> list[dict[str, str]]:
    pair = normalize_pair_name(pair_name)
    return [row for row in normalize_allowed_slices(allowed_slices) if row["pair_name"] == pair]


def get_pair_config(pair_name: str) -> dict[str, Any]:
    pair = normalize_pair_name(pair_name)
    if pair not in PAIR_CONFIGS:
        raise MinimalConfigError(f"Unknown pair_name: {pair}")
    return deepcopy(PAIR_CONFIGS[pair])


def get_pair_mt5_symbol(pair_name: str) -> str:
    cfg = get_pair_config(pair_name)
    mt5_symbol = cfg.get("mt5_symbol") or DEFAULT_MT5_SYMBOL_BY_SYMBOL.get(str(cfg.get("symbol", "")).upper())
    return normalize_mt5_symbol(mt5_symbol)


def is_auto_trade_enabled(pair_name: str) -> bool:
    cfg = get_pair_config(pair_name)
    return bool(cfg.get("auto_trade_enabled", False))


def get_csv_filename(csv_key: str) -> str:
    key = str(csv_key or "").strip()
    if key not in CSV_KEYS:
        raise MinimalConfigError(f"Unknown csv_key: {csv_key!r}")
    return CSV_KEYS[key]


def resolve_csv_path(
    csv_dir: str | Path,
    csv_key: str,
    overrides: Mapping[str, str | Path | None] | None = None,
) -> Path:
    """Resolve one CSV path from overrides or csv_dir + CSV_KEYS.

    `overrides` may be keyed by csv_key, for example {"gold_m5": "C:/.../goldsharp_m5.csv"}.
    """
    key = str(csv_key or "").strip()
    if overrides and key in overrides and overrides[key]:
        return Path(str(overrides[key]))
    return Path(csv_dir) / get_csv_filename(key)


def get_timeframe_minutes(timeframe: str) -> int:
    tf = str(timeframe or "").strip().upper()
    if tf not in TIMEFRAME_MINUTES:
        raise MinimalConfigError(f"Unknown timeframe: {timeframe!r}")
    return TIMEFRAME_MINUTES[tf]


def get_pair_allowed_slice_set(pair_name: str) -> set[str]:
    cfg = get_pair_config(pair_name)
    pair = cfg["pair_name"]
    return {
        allowed_slice_to_string({"pair_name": pair, **row})
        for row in cfg.get("allowed_slices", [])
    }


def validate_allowed_slices_against_pair_configs(
    allowed_slices: Iterable[Mapping[str, Any] | str] | None = None,
) -> list[dict[str, str]]:
    """Validate that allowed slices are known and supported by each pair config."""
    normalized = normalize_allowed_slices(allowed_slices)
    for row in normalized:
        pair_name = row["pair_name"]
        supported = get_pair_allowed_slice_set(pair_name)
        slice_text = allowed_slice_to_string(row)
        if slice_text not in supported:
            raise MinimalConfigError(
                f"Allowed slice is not supported by pair config: {slice_text}; supported={sorted(supported)}"
            )
    return normalized


def build_csv_overrides_from_args(args: Any) -> dict[str, str | None]:
    """Build csv_key -> path override mapping from argparse-style attributes.

    This helper accepts attributes like `gold_m5_csv`, `btc_h4_csv`, etc.
    Missing attributes are ignored.
    """
    mapping = {
        "gold_m5": "gold_m5_csv",
        "gold_m15": "gold_m15_csv",
        "gold_h1": "gold_h1_csv",
        "gold_h4": "gold_h4_csv",
        "gold_d1": "gold_d1_csv",
        "btc_m5": "btc_m5_csv",
        "btc_m15": "btc_m15_csv",
        "btc_h1": "btc_h1_csv",
        "btc_h4": "btc_h4_csv",
    }
    out: dict[str, str | None] = {}
    for csv_key, attr in mapping.items():
        value = getattr(args, attr, None)
        if value:
            out[csv_key] = str(value)
    return out


__all__ = [
    "CSV_KEYS",
    "DEFAULT_ALLOWED_SLICES",
    "DEFAULT_MT5_SYMBOL_BY_SYMBOL",
    "DEFAULT_TAIL_BARS",
    "MinimalConfigError",
    "PAIR_CONFIGS",
    "TIMEFRAME_MINUTES",
    "allowed_slice_to_string",
    "build_csv_overrides_from_args",
    "filter_allowed_slices_for_pair",
    "get_csv_filename",
    "get_pair_allowed_slice_set",
    "get_pair_config",
    "get_pair_mt5_symbol",
    "get_required_pair_names",
    "get_timeframe_minutes",
    "is_auto_trade_enabled",
    "normalize_allowed_slice",
    "normalize_allowed_slices",
    "normalize_mt5_symbol",
    "normalize_symbol",
    "resolve_csv_path",
    "validate_allowed_slices_against_pair_configs",
]

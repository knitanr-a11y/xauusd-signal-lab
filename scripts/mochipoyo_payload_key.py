#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stable payload_key builder for Mochipoyo live notifications.

The payload_key must identify the signal itself, not the filter path that found
it.  Therefore unstable fields such as source_filter_name, reason_text,
risk_status, spread metrics, and Discord message text are intentionally excluded.

Canonical format:
    symbol|pair_name|candidate_rank|direction|signal_close_time|entry_time|entry_price_normalized

Price normalization is currently fixed to 2 decimals for both GOLD and BTC by
pair config, but the builder accepts `price_digits` for future reuse.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

import pandas as pd

PAYLOAD_KEY_STATUS_OK = "OK"
PAYLOAD_KEY_STATUS_INVALID_MISSING_FIELD = "INVALID_MISSING_FIELD"
PAYLOAD_KEY_STATUS_INVALID_PRICE = "INVALID_PRICE"
PAYLOAD_KEY_STATUS_INVALID_TIME = "INVALID_TIME"

PAYLOAD_REQUIRED_FIELDS = (
    "symbol",
    "pair_name",
    "candidate_rank",
    "direction",
    "signal_close_time",
    "entry_time",
    "entry_price",
)


@dataclass(frozen=True)
class PayloadKeyResult:
    payload_key: str | None
    payload_key_status: str
    entry_price_normalized: str | None
    error_reason: str | None = None


def _get_field(row_or_fields: Mapping[str, Any] | None, name: str, explicit: Any = None) -> Any:
    if explicit is not None:
        return explicit
    if row_or_fields is None:
        return None
    return row_or_fields.get(name)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    if isinstance(value, str) and not value.strip():
        return True
    return False


def normalize_symbol(symbol: Any) -> str:
    value = str(symbol or "").strip().upper()
    if not value:
        raise ValueError("symbol is required")
    return value


def normalize_pair_name(pair_name: Any) -> str:
    value = str(pair_name or "").strip().upper()
    if not value:
        raise ValueError("pair_name is required")
    return value


def normalize_candidate_rank(candidate_rank: Any) -> str:
    value = str(candidate_rank or "").strip().upper()
    if not value:
        raise ValueError("candidate_rank is required")
    return value


def normalize_direction(direction: Any) -> str:
    value = str(direction or "").strip().upper()
    if value not in {"BUY", "SELL"}:
        raise ValueError(f"direction must be BUY or SELL, got {direction!r}")
    return value


def format_signal_time(value: Any) -> str:
    """Format a signal/entry time as YYYY-MM-DD HH:MM:SS."""
    if _is_missing(value):
        raise ValueError("time is required")
    if isinstance(value, pd.Timestamp):
        ts = value
    elif isinstance(value, datetime):
        ts = pd.Timestamp(value)
    else:
        ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"invalid time value: {value!r}")
    # Keep naive/local CSV time semantics.  If a timezone-aware value arrives,
    # drop the tz after converting to its represented wall time.
    try:
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.tz_localize(None)
    except TypeError:
        # Some pandas objects raise when already tz-naive; ignore.
        pass
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def normalize_price(value: Any, digits: int = 2) -> str:
    """Normalize price with Decimal ROUND_HALF_UP to a fixed number of decimals."""
    if _is_missing(value):
        raise ValueError("price is required")
    try:
        dec = Decimal(str(value).strip())
        if not dec.is_finite():
            raise ValueError("price is not finite")
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValueError(f"invalid price value: {value!r}") from exc
    if digits < 0:
        raise ValueError(f"digits must be >= 0, got {digits}")
    quantum = Decimal("1") if digits == 0 else Decimal("1").scaleb(-digits)
    rounded = dec.quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{rounded:.{digits}f}"


def build_payload_key(
    row_or_fields: Mapping[str, Any] | None = None,
    *,
    symbol: Any = None,
    pair_name: Any = None,
    candidate_rank: Any = None,
    direction: Any = None,
    signal_close_time: Any = None,
    entry_time: Any = None,
    entry_price: Any = None,
    price_digits: int = 2,
) -> PayloadKeyResult:
    """Build a stable payload key from row fields or explicit arguments."""
    values = {
        "symbol": _get_field(row_or_fields, "symbol", symbol),
        "pair_name": _get_field(row_or_fields, "pair_name", pair_name),
        "candidate_rank": _get_field(row_or_fields, "candidate_rank", candidate_rank),
        "direction": _get_field(row_or_fields, "direction", direction),
        "signal_close_time": _get_field(row_or_fields, "signal_close_time", signal_close_time),
        "entry_time": _get_field(row_or_fields, "entry_time", entry_time),
        "entry_price": _get_field(row_or_fields, "entry_price", entry_price),
    }
    missing = [name for name, value in values.items() if _is_missing(value)]
    if missing:
        return PayloadKeyResult(
            payload_key=None,
            payload_key_status=PAYLOAD_KEY_STATUS_INVALID_MISSING_FIELD,
            entry_price_normalized=None,
            error_reason="missing fields: " + ",".join(missing),
        )

    try:
        norm_symbol = normalize_symbol(values["symbol"])
        norm_pair_name = normalize_pair_name(values["pair_name"])
        norm_rank = normalize_candidate_rank(values["candidate_rank"])
        norm_direction = normalize_direction(values["direction"])
    except ValueError as exc:
        return PayloadKeyResult(
            payload_key=None,
            payload_key_status=PAYLOAD_KEY_STATUS_INVALID_MISSING_FIELD,
            entry_price_normalized=None,
            error_reason=str(exc),
        )

    try:
        norm_signal_time = format_signal_time(values["signal_close_time"])
        norm_entry_time = format_signal_time(values["entry_time"])
    except ValueError as exc:
        return PayloadKeyResult(
            payload_key=None,
            payload_key_status=PAYLOAD_KEY_STATUS_INVALID_TIME,
            entry_price_normalized=None,
            error_reason=str(exc),
        )

    try:
        entry_price_normalized = normalize_price(values["entry_price"], digits=price_digits)
    except ValueError as exc:
        return PayloadKeyResult(
            payload_key=None,
            payload_key_status=PAYLOAD_KEY_STATUS_INVALID_PRICE,
            entry_price_normalized=None,
            error_reason=str(exc),
        )

    payload_key = "|".join(
        [
            norm_symbol,
            norm_pair_name,
            norm_rank,
            norm_direction,
            norm_signal_time,
            norm_entry_time,
            entry_price_normalized,
        ]
    )
    return PayloadKeyResult(
        payload_key=payload_key,
        payload_key_status=PAYLOAD_KEY_STATUS_OK,
        entry_price_normalized=entry_price_normalized,
        error_reason=None,
    )


def build_logical_key(
    row_or_fields: Mapping[str, Any] | None = None,
    *,
    price_digits: int = 2,
    **kwargs: Any,
) -> tuple[str, str, str, str, str, str, str] | None:
    """Build a tuple logical key for comparison joins.

    Returns None if the payload key cannot be built.
    """
    result = build_payload_key(row_or_fields, price_digits=price_digits, **kwargs)
    if result.payload_key_status != PAYLOAD_KEY_STATUS_OK or result.payload_key is None:
        return None
    parts = result.payload_key.split("|")
    return tuple(parts)  # type: ignore[return-value]


def apply_payload_key_to_dataframe(
    df: pd.DataFrame,
    *,
    price_digits: int = 2,
) -> pd.DataFrame:
    """Return a copy of df with payload_key status columns applied row-by-row."""
    out = df.copy()
    payload_keys: list[str | None] = []
    statuses: list[str] = []
    normalized_prices: list[str | None] = []
    errors: list[str | None] = []
    for _, row in out.iterrows():
        result = build_payload_key(row.to_dict(), price_digits=price_digits)
        payload_keys.append(result.payload_key)
        statuses.append(result.payload_key_status)
        normalized_prices.append(result.entry_price_normalized)
        errors.append(result.error_reason)
    out["payload_key"] = payload_keys
    out["payload_key_status"] = statuses
    out["entry_price_normalized"] = normalized_prices
    out["payload_key_error_reason"] = errors
    return out


__all__ = [
    "PAYLOAD_KEY_STATUS_INVALID_MISSING_FIELD",
    "PAYLOAD_KEY_STATUS_INVALID_PRICE",
    "PAYLOAD_KEY_STATUS_INVALID_TIME",
    "PAYLOAD_KEY_STATUS_OK",
    "PAYLOAD_REQUIRED_FIELDS",
    "PayloadKeyResult",
    "apply_payload_key_to_dataframe",
    "build_logical_key",
    "build_payload_key",
    "format_signal_time",
    "normalize_candidate_rank",
    "normalize_direction",
    "normalize_pair_name",
    "normalize_price",
    "normalize_symbol",
]

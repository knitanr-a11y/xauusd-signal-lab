from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .timeutil import ensure_same_awareness, parse_dt


class Source(str, Enum):
    BASE = "BASE"
    STAGE280 = "STAGE280"
    STAGE281 = "STAGE281"
    SHORT_STRICT = "SHORT_STRICT"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class DecisionStatus(str, Enum):
    ACCEPTED_SHADOW = "ACCEPTED_SHADOW"
    REJECTED_SHADOW = "REJECTED_SHADOW"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    source: Source
    direction: Direction
    signal_dt: datetime
    entry_dt: datetime
    max_holding_minutes: int
    closed_bar: bool
    features_asof: datetime
    closed_bar_time: datetime
    time_basis: str
    source_candidate: str | None = None
    entry_price: float | None = None
    tp_price: float | None = None
    sl_price: float | None = None
    model_name: str | None = None
    model_version: str | None = None
    feature_contract_hash: str | None = None
    entry_spread_usd: float | None = None
    quote_age_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Candidate":
        required = {"candidate_id", "source", "direction", "signal_dt", "entry_dt", "max_holding_minutes", "closed_bar", "features_asof", "closed_bar_time", "time_basis"}
        missing = sorted(required - set(raw))
        if missing:
            raise ValueError(f"candidate missing fields: {missing}")
        payload = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        payload["source"] = Source(payload["source"])
        payload["direction"] = Direction(payload["direction"])
        for key in ("signal_dt", "entry_dt", "features_asof", "closed_bar_time"):
            payload[key] = parse_dt(payload[key])
        payload["max_holding_minutes"] = int(payload["max_holding_minutes"])
        payload["closed_bar"] = bool(payload["closed_bar"])
        return cls(**payload)

    def validate(self, expected_time_basis: str) -> None:
        ensure_same_awareness(self.signal_dt, self.entry_dt, self.features_asof, self.closed_bar_time)
        if self.time_basis != expected_time_basis:
            raise ValueError("time_basis mismatch")
        if not self.closed_bar:
            raise ValueError("open bar candidate is forbidden")
        if self.features_asof > self.signal_dt or self.closed_bar_time > self.signal_dt:
            raise ValueError("candidate uses unavailable data")
        if self.entry_dt < self.signal_dt:
            raise ValueError("entry_dt is earlier than signal_dt")
        if self.max_holding_minutes <= 0:
            raise ValueError("max_holding_minutes must be positive")
        if self.source == Source.SHORT_STRICT and self.direction != Direction.SHORT:
            raise ValueError("SHORT_STRICT candidate must be SHORT")


@dataclass(frozen=True)
class Resolution:
    candidate_id: str
    exit_dt: datetime
    pnl: float
    exit_reason: str
    resolved_from_observed_market: bool = True
    observed_asof: datetime | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Resolution":
        return cls(
            candidate_id=str(raw["candidate_id"]),
            exit_dt=parse_dt(raw["exit_dt"]),
            pnl=float(raw["pnl"]),
            exit_reason=str(raw["exit_reason"]),
            resolved_from_observed_market=bool(raw.get("resolved_from_observed_market", True)),
            observed_asof=parse_dt(raw["observed_asof"]) if raw.get("observed_asof") else None,
        )

    def validate(self) -> None:
        if not self.resolved_from_observed_market:
            raise ValueError("resolution must come from observed market data")
        if self.observed_asof is not None and self.observed_asof < self.exit_dt:
            raise ValueError("resolution reported before exit_dt")


@dataclass(frozen=True)
class Decision:
    candidate_id: str
    status: DecisionStatus
    reason: str
    dd_before_entry: float
    equity_before_entry: float
    peak_before_entry: float
    diagnostics: dict[str, Any] = field(default_factory=dict)

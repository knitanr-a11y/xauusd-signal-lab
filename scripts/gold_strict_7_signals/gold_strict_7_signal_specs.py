#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signal specifications for the isolated GOLD strict seven-candidate research set.

This file intentionally contains only declarative specs and small helpers.
It does not read CSVs, place orders, send Discord notifications, or call AI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["BUY", "SELL"]
SessionName = Literal["ALL", "LONDON", "NY", "LONDON_NY"]
FamilyName = Literal[
    "KC_CCI150",
    "SWEEP_RECLAIM_RSI",
    "STOCH_BB_KTURN",
    "DONCHIAN_MACD_RANGE",
    "BB_RSI_REJECTION",
]

GOLD_PIP_SIZE = 0.10
MIN_TP_PIPS = 20.0
DEFAULT_BROKER_SYMBOL = "GOLD#"
DEFAULT_SYMBOL = "GOLD"
DEFAULT_MAGIC_BASE = 26051970


@dataclass(frozen=True)
class GoldStrictSignalSpec:
    strategy_id: str
    family: FamilyName
    direction: Direction
    session: SessionName
    tp_pips: float
    sl_pips: float
    cooldown_minutes: int
    trigger_timeframe: str = "M5"
    outcome_timeframe: str = "M1"
    min_range_atr: float = 0.0
    donchian_lookback: int = 0
    cci_threshold: float = 150.0
    rsi_threshold: float = 30.0
    rejection_threshold: float = 0.65
    notes: str = ""

    @property
    def tp_price_distance(self) -> float:
        return float(self.tp_pips) * GOLD_PIP_SIZE

    @property
    def sl_price_distance(self) -> float:
        return float(self.sl_pips) * GOLD_PIP_SIZE

    @property
    def rr(self) -> float:
        if self.sl_pips <= 0:
            return 0.0
        return float(self.tp_pips) / float(self.sl_pips)

    @property
    def cooldown_bars_m5(self) -> int:
        return max(0, int(round(float(self.cooldown_minutes) / 5.0)))


GOLD_STRICT_7_SIGNAL_SPECS: list[GoldStrictSignalSpec] = [
    GoldStrictSignalSpec(
        strategy_id="SELL_KC_CCI150_LONDON_TP100_SL10",
        family="KC_CCI150",
        direction="SELL",
        session="LONDON",
        tp_pips=100.0,
        sl_pips=10.0,
        cooldown_minutes=60,
        cci_threshold=150.0,
        rejection_threshold=0.55,
        notes="Keltner/CCI reversal SELL candidate; strongest non-Donchian SELL family from exploration.",
    ),
    GoldStrictSignalSpec(
        strategy_id="BUY_SWEEP_RECLAIM_RSI_TP150_SL10",
        family="SWEEP_RECLAIM_RSI",
        direction="BUY",
        session="LONDON_NY",
        tp_pips=150.0,
        sl_pips=10.0,
        cooldown_minutes=30,
        rsi_threshold=35.0,
        rejection_threshold=0.55,
        notes="Liquidity sweep/reclaim BUY with RSI context; large-target reclaim candidate.",
    ),
    GoldStrictSignalSpec(
        strategy_id="BUY_STOCH_BB_KTURN_NY_TP150_SL10",
        family="STOCH_BB_KTURN",
        direction="BUY",
        session="NY",
        tp_pips=150.0,
        sl_pips=10.0,
        cooldown_minutes=60,
        rejection_threshold=0.50,
        notes="Stochastic + Bollinger reversal BUY with Stoch K > D added after April weakness analysis.",
    ),
    GoldStrictSignalSpec(
        strategy_id="SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5",
        family="DONCHIAN_MACD_RANGE",
        direction="SELL",
        session="NY",
        tp_pips=30.0,
        sl_pips=7.5,
        cooldown_minutes=120,
        donchian_lookback=48,
        min_range_atr=1.5,
        notes="H1 trend + Donchian48 low break + MACD + range >= 1.5 SELL candidate.",
    ),
    GoldStrictSignalSpec(
        strategy_id="SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120",
        family="DONCHIAN_MACD_RANGE",
        direction="SELL",
        session="ALL",
        tp_pips=150.0,
        sl_pips=37.5,
        cooldown_minutes=120,
        donchian_lookback=96,
        min_range_atr=1.5,
        notes="H1 trend + Donchian96 low break + MACD + range >= 1.5, safer/lower-frequency CD120 variant.",
    ),
    GoldStrictSignalSpec(
        strategy_id="SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60",
        family="DONCHIAN_MACD_RANGE",
        direction="SELL",
        session="ALL",
        tp_pips=150.0,
        sl_pips=37.5,
        cooldown_minutes=60,
        donchian_lookback=96,
        min_range_atr=1.5,
        notes="H1 trend + Donchian96 low break + MACD + range >= 1.5, more frequent CD60 variant.",
    ),
    GoldStrictSignalSpec(
        strategy_id="BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5",
        family="BB_RSI_REJECTION",
        direction="BUY",
        session="NY",
        tp_pips=30.0,
        sl_pips=7.5,
        cooldown_minutes=30,
        rsi_threshold=30.0,
        rejection_threshold=0.65,
        notes="Bollinger Band + RSI30 + rejection candle BUY candidate, shorter target than sweep/stoch families.",
    ),
]


def get_signal_specs() -> list[GoldStrictSignalSpec]:
    return list(GOLD_STRICT_7_SIGNAL_SPECS)


def get_signal_spec_by_id(strategy_id: str) -> GoldStrictSignalSpec:
    for spec in GOLD_STRICT_7_SIGNAL_SPECS:
        if spec.strategy_id == strategy_id:
            return spec
    raise KeyError(f"unknown GOLD strict signal strategy_id: {strategy_id}")


def validate_signal_specs() -> None:
    seen: set[str] = set()
    for spec in GOLD_STRICT_7_SIGNAL_SPECS:
        if spec.strategy_id in seen:
            raise ValueError(f"duplicate strategy_id: {spec.strategy_id}")
        seen.add(spec.strategy_id)
        if spec.tp_pips < MIN_TP_PIPS:
            raise ValueError(f"{spec.strategy_id}: tp_pips must be >= {MIN_TP_PIPS}; got {spec.tp_pips}")
        if spec.sl_pips <= 0:
            raise ValueError(f"{spec.strategy_id}: sl_pips must be positive")
        if spec.trigger_timeframe != "M5":
            raise ValueError(f"{spec.strategy_id}: trigger_timeframe must currently be M5")
        if spec.outcome_timeframe != "M1":
            raise ValueError(f"{spec.strategy_id}: outcome_timeframe must currently be M1")


if __name__ == "__main__":
    validate_signal_specs()
    for item in GOLD_STRICT_7_SIGNAL_SPECS:
        print(f"{item.strategy_id}: {item.direction} {item.family} TP={item.tp_pips}p SL={item.sl_pips}p session={item.session}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Declarative specs for the BTC strict five-candidate research set.

This module is intentionally side-effect free:
- no CSV reads
- no MT5 calls
- no Discord calls
- no AI calls
- no runtime ledger mutation

The five baseline candidates are the CD0 set selected after the initial
confirmed-time, spread-aware exploration.  D1 is intentionally not part of the
baseline signal rules.  H1/H4 context, when used, must be joined by confirmed
close time only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["BUY", "SELL"]
FamilyName = Literal[
    "DONCHIAN_BREAKDOWN",
    "RSI_RECLAIM",
    "CCI_RECLAIM",
]

BTC_PIP_SIZE = 10.0
BTC_POINT_SIZE = 0.01
DEFAULT_SYMBOL = "BTC"
DEFAULT_BROKER_SYMBOL = "BTCUSD#"
DEFAULT_MAGIC_BASE = 26052050

# Frozen thresholds from the 2026-05-20 BTC strict-5 exploration.
# These are constants, not dynamically re-estimated from the full backtest CSV
# during signal generation.  Recomputing quantiles inside a backtest would leak
# future distribution information.
FROZEN_M15_BB_WIDTH_Q40 = 0.008303356874603023
FROZEN_M15_ATR14_Q30 = 193.10767024904803
FROZEN_M15_ATR14_Q80 = 358.1778267992429


@dataclass(frozen=True)
class BtcStrictSignalSpec:
    strategy_id: str
    candidate_base: str
    family: FamilyName
    direction: Direction
    tp_price_distance: float
    sl_price_distance: float
    horizon_m15: int
    cooldown_bars_m15: int = 0
    trigger_timeframe: str = "M15"
    outcome_timeframe: str = "M5"
    notes: str = ""

    @property
    def tp_pips(self) -> float:
        return float(self.tp_price_distance) / BTC_PIP_SIZE

    @property
    def sl_pips(self) -> float:
        return float(self.sl_price_distance) / BTC_PIP_SIZE

    @property
    def rr(self) -> float:
        if self.sl_price_distance <= 0:
            return 0.0
        return float(self.tp_price_distance) / float(self.sl_price_distance)

    @property
    def horizon_minutes(self) -> int:
        return int(self.horizon_m15) * 15


BTC_STRICT_5_SIGNAL_SPECS: list[BtcStrictSignalSpec] = [
    BtcStrictSignalSpec(
        strategy_id="BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200_TP1900_SL400_H20H_CD0",
        candidate_base="BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200",
        family="DONCHIAN_BREAKDOWN",
        direction="SELL",
        tp_price_distance=1900.0,
        sl_price_distance=400.0,
        horizon_m15=80,
        notes=(
            "M15 Donchian96 breakdown with M15 close < EMA200 and frozen "
            "BB-width low-volatility filter. No D1 condition."
        ),
    ),
    BtcStrictSignalSpec(
        strategy_id="BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06_TP2500_SL750_H4H_CD0",
        candidate_base="BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06",
        family="DONCHIAN_BREAKDOWN",
        direction="SELL",
        tp_price_distance=2500.0,
        sl_price_distance=750.0,
        horizon_m15=16,
        notes=(
            "M15 Donchian32 breakdown, confirmed H1 EMA20 slope down, frozen "
            "M15 ATR14 Q30-Q80 filter, MT5 hours 00-06. No D1 condition."
        ),
    ),
    BtcStrictSignalSpec(
        strategy_id="BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0",
        candidate_base="BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23",
        family="RSI_RECLAIM",
        direction="BUY",
        tp_price_distance=2300.0,
        sl_price_distance=650.0,
        horizon_m15=80,
        notes=(
            "M15 RSI14 reclaim above 40, bullish candle, close > EMA200, "
            "frozen BB-width low-volatility filter, MT5 hours 12-23. No D1 condition."
        ),
    ),
    BtcStrictSignalSpec(
        strategy_id="BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06_TP2400_SL600_H6H_CD0",
        candidate_base="BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06",
        family="DONCHIAN_BREAKDOWN",
        direction="SELL",
        tp_price_distance=2400.0,
        sl_price_distance=600.0,
        horizon_m15=24,
        notes=(
            "M15 Donchian64 strong lower close breakdown, confirmed H1 MACD "
            "histogram < 0, M15 range/ATR 0.8-2.0, MT5 hours 00-06. No D1 condition."
        ),
    ),
    BtcStrictSignalSpec(
        strategy_id="BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0",
        candidate_base="BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23",
        family="CCI_RECLAIM",
        direction="BUY",
        tp_price_distance=2500.0,
        sl_price_distance=650.0,
        horizon_m15=80,
        notes=(
            "M15 CCI20 reclaim above -100, bullish candle, confirmed H4 "
            "EMA20 > EMA50, frozen BB-width low-volatility filter, MT5 hours "
            "19-23. No D1 condition."
        ),
    ),
]


def get_signal_specs() -> list[BtcStrictSignalSpec]:
    return list(BTC_STRICT_5_SIGNAL_SPECS)


def get_signal_spec_by_id(strategy_id: str) -> BtcStrictSignalSpec:
    for spec in BTC_STRICT_5_SIGNAL_SPECS:
        if spec.strategy_id == strategy_id:
            return spec
    raise KeyError(f"unknown BTC strict signal strategy_id: {strategy_id}")


def validate_signal_specs() -> None:
    seen: set[str] = set()
    bases: set[str] = set()
    for spec in BTC_STRICT_5_SIGNAL_SPECS:
        if spec.strategy_id in seen:
            raise ValueError(f"duplicate strategy_id: {spec.strategy_id}")
        if spec.candidate_base in bases:
            raise ValueError(f"duplicate candidate_base: {spec.candidate_base}")
        seen.add(spec.strategy_id)
        bases.add(spec.candidate_base)
        if spec.trigger_timeframe != "M15":
            raise ValueError(f"{spec.strategy_id}: trigger_timeframe must be M15")
        if spec.outcome_timeframe != "M5":
            raise ValueError(f"{spec.strategy_id}: outcome_timeframe must be M5")
        if spec.cooldown_bars_m15 != 0:
            raise ValueError(f"{spec.strategy_id}: BTC strict 5 baseline is CD0")
        if spec.tp_price_distance < 500.0:
            raise ValueError(f"{spec.strategy_id}: TP must be >= 500 price distance / 50 pips")
        if spec.sl_price_distance <= 0:
            raise ValueError(f"{spec.strategy_id}: SL must be positive")
        if spec.horizon_m15 <= 0:
            raise ValueError(f"{spec.strategy_id}: horizon_m15 must be positive")


if __name__ == "__main__":
    validate_signal_specs()
    for item in BTC_STRICT_5_SIGNAL_SPECS:
        print(
            f"{item.strategy_id}: {item.direction} {item.family} "
            f"TP={item.tp_pips:.1f}p SL={item.sl_pips:.1f}p "
            f"H={item.horizon_m15} M15"
        )

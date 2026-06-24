# GOLD V3 Stage318 — Mochipoyo High-Confidence Refinement

## Purpose

Stage317 found a valid unified Mochipoyo SHORT research watch:

- M5/H4
- SHORT
- RR1.5
- ATR ratio at least 1.0
- round-number-near excluded

Stage318 does not replace or rewrite Stage317. It tests whether a higher-confidence subset can raise win rate while preserving most of the Stage317 edge.

## Fixed source

Stage318 accepts only the exact Stage317 selected candidate:

`M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`

The Stage317 JSON status, selected candidate key, and selected CSV SHA256 must all match before the audit runs.

## Fixed market-state profiles

No time-of-day or 2026-derived rule is introduced. The following fixed profiles use only fields already saved in the Stage317 trade registry:

- `BASE`
- `ATR_STEADY_1_10_TO_1_45`
- `ACTIVE_RANGE_0_70_TO_1_05`
- `TREND_FLOW_COMPRESSION_GE_0_95`
- `ATR_STEADY_AND_ACTIVE_RANGE`
- `ATR_STEADY_AND_FLOW`
- `CONSENSUS_2PLUS`
- `CONSENSUS_OR_ATR_STEADY_AND_RANGE`
- `CONSENSUS_OR_ATR_STEADY_AND_FLOW`

Interpretation:

- ATR steady band removes both barely-active and excessively-expanded volatility.
- Active range requires a meaningful but non-climax signal candle.
- Trend-flow compression ratio at least 0.95 avoids short-range contraction relative to the previous 40-bar median.
- Consensus requires at least two Mochipoyo alert families to describe the same exact entry.

## Selection years

- 2024 and 2025 only for selection
- 2026 display only
- 2026 is not a clean holdout

## Primary gate

The primary candidate must satisfy all of the following on 2024–2025:

- at least 20 trades
- at least 8 trades in each year
- win rate at least 60%
- win-rate improvement of at least 4 percentage points over Stage317
- win rate at least 55% in each year
- profit factor at least 1.35
- positive total R
- retain at least 70% of Stage317 total R
- no worse maximum drawdown than Stage317
- largest winner share no more than 35%

This gate is designed to raise win rate without accepting a tiny or highly concentrated sample.

## Premium sparse gate

A separate sparse watch may be reported when it has:

- at least 12 trades
- at least 5 trades in each year
- win rate at least 68%
- win rate at least 60% in each year
- profit factor at least 1.50
- positive total R
- no worse maximum drawdown than Stage317
- largest winner share no more than 35%

A sparse pass cannot replace the primary candidate and cannot be promoted automatically.

## Outputs

- `stage318_mochipoyo_high_confidence_refinement.json`
- `stage318_mochipoyo_high_confidence_all_profiles.csv`
- `stage318_primary_high_confidence_trades.csv`
- `stage318_premium_sparse_watch_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage317 research watch unchanged
- Stage314 future-only prospective contract unchanged
- Stage315 independent research unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF

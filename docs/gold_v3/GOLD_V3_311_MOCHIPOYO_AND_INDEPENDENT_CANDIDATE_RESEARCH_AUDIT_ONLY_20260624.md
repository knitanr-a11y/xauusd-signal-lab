# GOLD V3 Stage311 — Mochipoyo and Independent Candidate Research

## Purpose

Return to candidate research. Stage311 does not depend on the missing Stage284/286 historical portfolio ledger and does not continue the Stage310 file search.

The registered Stage307 top ensemble remains an unchanged research reference.

## Mochipoyo tracks

The documented method is translated into four separate tracks instead of one broad mixed score:

1. `MOCHI_EARLY_PULLBACK`
   - higher and lower timeframe EMA20/30/40 alignment
   - pullback to EMA20 area
   - MACD 6/13/4 acceleration
   - RCI 9/14 turn or hidden divergence
   - moderate/high volatility
   - late extension and climax avoidance

2. `MOCHI_HIDDEN_PULLBACK`
   - trend-aligned pullback
   - confirmed hidden MACD divergence on the main or higher timeframe
   - RCI turn or MACD acceleration

3. `MOCHI_HTF_RCI_RESUME`
   - higher timeframe trend
   - higher timeframe RCI turn
   - lower timeframe RCI turn and MACD acceleration

4. `MOCHI_ROLL_RETEST`
   - trend-aligned break and retest
   - RCI/hidden-divergence confirmation
   - only on M5/H4 and M15/H4

The implementation does not claim to reproduce the proprietary Mochipoyo alert formula. It objectively tests the method documented in the supplied guide.

## Independent tracks

1. `COMPRESSION_BREAKOUT_CONT`
   - prior eight-bar range compression versus the prior 40-bar median
   - higher/lower timeframe trend alignment
   - directional 20-bar breakout
   - expansion candle without a climax bar

2. `SWEEP_RECLAIM_REVERSAL`
   - sweep beyond the prior 20-bar extreme
   - close back through the level
   - regular divergence or higher-timeframe RCI turn
   - RCI turn or MACD acceleration
   - strong opposite higher-timeframe trend excluded

## Timeframe pairs

- M5 / H4
- M15 / H4
- H1 / D1

The two independent tracks are limited to M5/H4 and M15/H4.

## Exits

- 1.25R
- 1.50R
- opposite RCI 70 arrival
- confirmed structural target

Stops use the Stage308 confirmed ZigZag structure contract with minimum 0.75 ATR and maximum 2.0 ATR risk distance.

## Selection protocol

- 2024: development
- 2025: unchanged confirmation
- 2026: display only

2026 is not used in candidate selection or ranking.

A research lead requires on 2024+2025:

- at least 30 combined trades
- at least 10 trades in each year
- PF at least 1.10 in each year
- positive R in each year
- combined PF at least 1.25
- combined drawdown no more than 10R
- largest winner share no more than 40%

The selected pools use only candidates passing that fixed 2024/2025 gate. Multiple exits for the same signal contract are not added together.

## Stage307 reference

When the Stage309 trade CSV is available, Stage311 reports exact-entry and holding-period overlap between the new selected pools and:

`GOLD_V3_STAGE307_TOP_REV_LONG_ANY_P90`

This is a reference diagnostic only. Stage307 is not changed or promoted.

## Outputs

- `stage311_mochipoyo_and_independent_candidate_research.json`
- `stage311_candidate_research_all_trades.csv`
- `stage311_selected_lead_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage280 remains blocked
- Stage307 top remains a registered research candidate
- Stage292 candidate pool unchanged
- final signal unchanged
- automatic MT5 order OFF
- Discord OFF
- partial close OFF

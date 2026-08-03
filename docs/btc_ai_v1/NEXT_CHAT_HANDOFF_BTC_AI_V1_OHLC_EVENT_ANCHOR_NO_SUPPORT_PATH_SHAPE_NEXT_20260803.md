# NEXT CHAT HANDOFF — BTC AI V1 OHLC event-anchor forensic complete, no directional survivor, path-shape next

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_OHLC_EVENT_ANCHORS_EXPLAIN_MAGNITUDE_NO_STABLE_DIRECTIONAL_SURVIVOR`

## Authority

Use only the accepted XM `BTCUSD#` closed-bar OHLC snapshot.

- M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- no external data or volume fields
- fixed spread remains 22.50 USD for later candidate stages
- no candidate PnL or 2026 was opened in this forensic stage

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
3. `docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`
4. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
5. `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESULT_20260803.md`
6. `config/btc_ai_v1/ohlc_event_anchor_survival_forensic_contract_20260803.json`
7. `config/btc_ai_v1/ohlc_event_anchor_survival_bin_addendum_20260803.json`
8. `config/btc_ai_v1/ohlc_event_anchor_matched_baseline_correction_20260803.json`
9. `docs/btc_ai_v1/BTC_AI_V1_OHLC_EVENT_ANCHOR_SURVIVAL_RESULT_20260803.md`
10. `config/btc_ai_v1/ohlc_event_anchor_survival_result_20260803.json`
11. `docs/btc_ai_v1/BTC_AI_V1_OHLC_EVENT_ANCHOR_SURVIVAL_REPRODUCIBILITY_MANIFEST_20260803.md`
12. `config/btc_ai_v1/current_state_20260803.json`
13. `config/btc_ai_v1/next_action_20260803.json`
14. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

## Completed forensic

Development-only analysis covered exactly 24 calendar months, 2024-01 through 2025-12.

Preregistered six anchor families:

1. 20-bar range break
2. causal 20-bar swing turn
3. compression-expansion candle
4. named phase-transition start
5. failed 20-bar range break
6. EMA20 slope turn

Counts:

- 28,355 directed anchor events
- six families
- 15 subtypes
- maximum 32 M15 follow-up bars
- continuation barrier +1.00 ATR
- reversal barrier -0.75 ATR
- reversal-first same-bar collision

## Critical design correction

The first raw analysis incorrectly showed 13 support passes. This result is void because the asymmetric barriers and reversal-first rule structurally bias raw rates toward reversal.

A correction was frozen before matched-baseline outcomes:

- match by half-year
- D1 regime
- maturity-distance bin
- direction
- same barriers and collision rule
- exclude exact evaluated subtype timestamp/direction rows

Only the corrected result is authoritative.

## Corrected result

- corrected forensic support survivors: **0**
- candidate PnL opened: no
- 2026 opened: no

Largest effects:

- `COMPRESSION_EXPANSION_DOWN`: 128 events / 24 months = 5.33/month; incremental continuation-minus-reversal -0.1180; stable sign but insufficient total and half-year density.
- `RANGE_BREAK_20_DOWN`: 2,828 / 24 = 117.83/month; incremental -0.0382; sign changed in 2025H1 and by D1 regime.
- `RANGE_BREAK_20_UP`: 3,237 / 24 = 134.88/month; incremental -0.0332; stable sign but below the frozen five-point effect gate.
- `FAILED_DOWN_BREAK -> UP`: 1,916 / 24 = 79.83/month; incremental +0.0207 in the same direction across all four half-years; stable but too weak.

## Main finding

Event anchors explained future excursion magnitude more clearly than fixed direction.

At four M15 bars versus matched ordinary states:

- compression-expansion UP: MFE +1.0160 ATR, MAE +0.4427 ATR
- compression-expansion DOWN: MFE +0.7274 ATR, MAE +0.5155 ATR
- range break DOWN: MFE +0.4290 ATR, MAE +0.1722 ATR

At eight bars, compression-expansion added approximately +0.82 to +0.87 ATR of pullback as well.

Therefore an expansion anchor identifies large two-sided movement and path turbulence, not an invariant directional entry.

Formal conclusion:

`EVENT_ANCHORS_EXPLAIN_EXCURSION_MAGNITUDE_BUT_NO_PREREGISTERED_ANCHOR_HAS_STABLE_INCREMENTAL_DIRECTIONAL_SURVIVAL_EDGE`

Formal supported candidates remain 0.

## Next stage

`BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_CONDITIONAL_MODEL_PREREGISTRATION`

The next distinct design must retain every anchor family and model the state after the anchor:

- bars since anchor
- directional ATR distance from anchor
- MFE already achieved
- adverse excursion already experienced
- pullback from post-anchor extreme
- acceptance/rejection after anchor
- H1/H4/D1 state
- continuation/reversal hazard at the next step

Required separation:

1. magnitude model: future absolute MFE/MAE and volatility
2. direction model: incremental continuation versus reversal relative to matched baseline

Transfer requirements must be frozen across all four half-years and D1 UP/NEUTRAL/DOWN before any exact-M1 PnL shortlist.

## Hard boundaries

- no external or volume data
- no use of 2026 for selection or support
- do not cite the invalid raw 13 passes
- do not rescue sparse compression-expansion or weak failed-break signals
- do not combine anchors after outcomes
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal
- do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO

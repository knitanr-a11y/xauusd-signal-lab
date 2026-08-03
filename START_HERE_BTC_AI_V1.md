# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_OHLC_EVENT_ANCHORS_EXPLAIN_MAGNITUDE_NO_STABLE_DIRECTIONAL_SURVIVOR`
- updated: `2026-08-03`

## Authority

Use only the accepted XM `BTCUSD#` closed-bar OHLC snapshot:

- M1 / M5 / M15 / H1 / H4 / D1
- MT5 broker-server time
- fixed spread: 22.50 USD per completed 1 BTC trade
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features

Old BTC BCR, old stacking and old frozen BTC candidates are not authority. Do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.

The unsolicited external-data work was rejected by the user. Related workflows, contracts, reports, handoff and download/probe scripts were removed from the current branch tree. Git history retains that incident only for audit.

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_EVENT_ANCHOR_NO_SUPPORT_PATH_SHAPE_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
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
14. `config/btc_ai_v1/source_data_manifest_20260803.json`
15. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
16. `config/btc_ai_v1/frequency_reporting_contract_20260803.json`
17. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or deleted external-data paths before completing this order.

## Established 2026 root cause

The 2024–2025 winners failed in 2026 because the same high-score OHLC shape changed from an early bearish impulse/correction into a mature and extended selloff. Generic SHORT opportunity remained, but score ordering collapsed and stop-first outcomes increased.

Formal root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## Previous OHLC model results

All development cycles below used exactly 24 calendar months, 2024-01 through 2025-12. The consumed 2026 seven-month period was not opened unless explicitly stated in older completed cycles.

- global state model: maximum PF 1.1302; survivors 0
- phase experts: maximum PF 1.4538; failed density/transfer; survivors 0
- transition experts: maximum PF 1.6162; failed density/time/regime transfer; survivors 0
- LightGBM sequence baseline: maximum PF 1.1539; 580 trades / 24 months = 24.17/month; 13 positive months; survivors 0
- GRU multi-task: maximum PF 1.1496; 363 / 24 = 15.13/month; 13 positive months; unstable by time and D1 regime; survivors 0

OHLC sequences contained measurable MFE/MAE information, but general models did not create stable fixed-payoff ordering.

## Completed event-anchor survival forensic

Preregistered six causal OHLC anchor families:

1. 20-bar range break
2. causal 20-bar swing turn
3. expansion after compression
4. named phase-transition start
5. failed 20-bar range break
6. EMA20 slope turn

Counts:

- 28,355 directed events
- six families
- 15 subtypes
- exactly 24 calendar months
- maximum 32 M15 follow-up bars

### Critical correction

The first raw analysis showed 13 support passes, but this result is invalid. The 1.00 ATR continuation barrier versus 0.75 ATR reversal barrier and reversal-first collision rule structurally biased raw outcomes toward reversal.

A matched baseline was frozen before corrected outcomes, matching:

- half-year
- D1 regime
- maturity-distance bin
- direction

Only the corrected result is authoritative.

### Corrected result

- corrected forensic support survivors: **0**
- candidate PnL opened: no
- 2026 opened: no

Largest corrected effects:

- `COMPRESSION_EXPANSION_DOWN`: 128 events / 24 months = 5.33/month; incremental outcome difference -0.1180; stable sign but insufficient density
- `RANGE_BREAK_20_DOWN`: 2,828 / 24 = 117.83/month; incremental -0.0382; unstable across time and D1 state
- `RANGE_BREAK_20_UP`: 3,237 / 24 = 134.88/month; incremental -0.0332; stable sign but below the frozen five-point gate
- `FAILED_DOWN_BREAK -> UP`: 1,916 / 24 = 79.83/month; incremental +0.0207 in all four half-years; stable but too weak

Main finding:

- anchors explained future excursion magnitude more clearly than fixed direction
- compression-expansion increased four-bar MFE by approximately +0.73 to +1.02 ATR
- it also increased MAE and eight-bar pullback by approximately +0.82 to +0.87 ATR
- therefore expansion anchors identify two-sided movement and path turbulence, not an invariant immediate entry direction

Formal conclusion:

`EVENT_ANCHORS_EXPLAIN_EXCURSION_MAGNITUDE_BUT_NO_PREREGISTERED_ANCHOR_HAS_STABLE_INCREMENTAL_DIRECTIONAL_SURVIVAL_EDGE`

Formal supported candidates remain **0**.

## Current next stage

`BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_CONDITIONAL_MODEL_PREREGISTRATION`

The next design must retain all six anchor families and model the evolving state after an anchor:

- bars since anchor
- directional ATR distance from anchor
- MFE and MAE already observed
- pullback from the post-anchor extreme
- acceptance or rejection through the anchor level
- current M15 phase/transition
- closed H1/H4/D1 state

Magnitude prediction and directional matched-baseline residual prediction must be separated. Transfer across all four half-years and D1 UP/NEUTRAL/DOWN is required before any exact-M1 PnL shortlist.

## Hard boundaries

- do not cite the invalid raw 13 passes
- do not rescue sparse compression-expansion or weak failed-break patterns
- no anchor combination after outcome inspection
- no post-result D1 filter or barrier change
- no use of 2026 for selection or support
- no external or volume data
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal
- every stage must leave dated contracts, results, current state, next action and next-chat handoff

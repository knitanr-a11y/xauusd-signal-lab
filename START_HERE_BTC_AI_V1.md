# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_OHLC_STATIC_AND_DELAYED_CONFIRMATION_NO_DIRECTIONAL_SURVIVOR`
- updated: `2026-08-03`

## Authority

Use only accepted XM `BTCUSD#` closed-bar OHLC:

- M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- closed M15 decisions and exact M1 execution
- fixed spread 22.50 USD per completed 1 BTC trade
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features

Old BTC BCR, stacking and frozen candidates are not authority. Do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_DELAYED_CONFIRMATION_NO_SUPPORT_ROLLING_ADAPTIVE_NEXT_20260803.md`

## Cumulative master package

- `BTC_AI_V1_MASTER_RESEARCH_PACKAGE_20260803_V3.zip`
- SHA256 `4a5d498cada1131bf84eb855016026fb889fdcbaad58cd840669fd04c3dfa53b`
- 689 files, approximately 270 MB, expansion-tested
- covers Stage 00 through Stage 30
- includes original stage ZIPs and extracted code/results
- excludes raw candles, GOLD and rejected external data

Manifest:

`docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_MASTER_PACKAGE_V3_MANIFEST_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. cumulative master manifest
4. `docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`
5. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
6. `docs/btc_ai_v1/BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_RESULT_20260803.md`
7. `config/btc_ai_v1/ohlc_anchor_age_path_shape_result_20260803.json`
8. `docs/btc_ai_v1/BTC_AI_V1_OHLC_DELAYED_CONFIRMATION_STATE_MACHINE_RESULT_20260803.md`
9. `config/btc_ai_v1/ohlc_delayed_confirmation_state_machine_result_20260803.json`
10. `config/btc_ai_v1/current_state_20260803.json`
11. `config/btc_ai_v1/next_action_20260803.json`
12. `config/btc_ai_v1/source_data_manifest_20260803.json`
13. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
14. `config/btc_ai_v1/frequency_reporting_contract_20260803.json`
15. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

## Established root cause

The 2024–2025 winners failed in 2026 because the same high-score OHLC shape changed from an early bearish impulse/correction into a mature and extended selloff. Generic SHORT opportunity remained, but score ordering collapsed and stop-first outcomes increased.

Formal root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## Research through Stage 28

- deterministic rules: local development survivors, robustness survivors 0
- binary ML: five finalists, all lost in the one-time untouched 2026 seven-month test
- diverse classifiers and continuous targets: local robustness survivors, all failed 2026 diagnosis
- pairwise ranking: no positive-net configurations
- phase/transition experts: local PF up to 1.6162 but failed density/time/D1 transfer
- sequence LightGBM/GRU: MFE/MAE information existed, fixed-payoff ordering unstable
- event anchors: explained two-sided excursion magnitude, corrected directional survivors 0

## Stage 29 — anchor age and path shape

- 42,018 anchors in 2023–2025
- 672,257 generated anchor-age rows
- 461,483 formal development rows / 24 months
- ordinary baseline 112,784 directed rows
- six families and fifteen subtypes retained

Magnitude:

- MFE improvement -0.0022; error worsened 1.54%
- MAE improvement +0.0004; error worsened 1.09%
- range improvement +0.0032; error worsened 2.18%
- support 0

Direction:

- residual Spearman 0.0541
- P90 selected 43,056 rows / 24 months = 1,794/month
- monthly min/median/max 1,025 / 1,755.5 / 2,602
- actual residual +0.0411 versus required +0.08
- D1 DOWN residual -0.0042
- support 0

Formal result:

`ANCHOR_AGE_PATH_SHAPE_ADDS_SMALL_UNSTABLE_DIRECTIONAL_RESIDUAL_AND_DOES_NOT_IMPROVE_MAGNITUDE_BASELINE`

## Stage 30 — delayed confirmation

First confirmation events:

- total 95,440 / 24 months
- actionable 70,892
- diagnostic 24,548

Actionable oriented residuals:

- failed acceptance/reclaim reversal: -0.0161
- deep pullback reversal: -0.0103
- mature extension reversal: +0.0081
- shallow pullback continuation: -0.0107
- accepted continuation: -0.0266
- adverse-dominant reversal: +0.0031

All six states had adequate density and all failed the frozen +0.08 effect and time/D1 transfer requirements.

Formal result:

`SIMPLE_DELAYED_CONFIRMATION_STATES_DO_NOT_CREATE_DIRECTIONAL_EDGE_BEYOND_CURRENT_OHLC_BASELINE`

## Current conclusion

Formal supported candidates remain **0**.

The directional problem was not solved by:

- more static OHLC features;
- model diversity;
- direct payoff/ranking targets;
- GRU sequences;
- phase/transition experts;
- anchor identity and maturity;
- static delayed ATR confirmation rules.

Stage 29 and 30 did not open candidate PnL or 2026.

## Current next stage

`BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_FORENSIC_PREREGISTRATION`

Test the drift mechanism directly:

- expanding versus rolling 3/6/12-month training
- monthly refit and past-only recalibration
- each next month in 2024–2025 evaluated once
- monthly AUC, label lift, calibration, PSI and D1 decomposition
- no PnL before stable ordering support
- 2026 diagnostic-only after schedule freeze

## Hard boundaries

- no external or volume data
- no use of 2026 for window, model, calibration or threshold selection
- no post-result month/D1/family/age/state filter
- no rescue or gate reduction
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal
- every count requires exact calendar months and monthly distribution
- every stage must leave contracts, results, state, next action, handoff and reproducibility artifacts

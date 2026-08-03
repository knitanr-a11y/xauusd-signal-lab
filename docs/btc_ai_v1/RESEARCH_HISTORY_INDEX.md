# BTC AI V1 — Research History Index

Chronological authority for `BTC_AI_CANDIDATE_RESEARCH_V1`.

Detailed code, all tables, incidents and original archives are contained in:

- `BTC_AI_V1_MASTER_RESEARCH_PACKAGE_20260803_V3.zip`
- SHA256 `4a5d498cada1131bf84eb855016026fb889fdcbaad58cd840669fd04c3dfa53b`
- manifest: `docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_MASTER_PACKAGE_V3_MANIFEST_20260803.md`

## Stage 00 / 00A — source acceptance and cost freeze

- accepted XM `BTCUSD#` closed OHLC M1/M5/M15/H1/H4/D1
- SHA256 frozen; no duplicates/null/OHLC violations
- exact M1 reaggregation parity passed
- gaps never filled
- MT5 broker-server time
- fixed spread 22.50 USD per completed 1 BTC trade

## Stage 01 — research design

- development 2024-01 through 2025-12, exactly 24 months
- four chronological expanding folds
- untouched 2026-01 through 2026-07 initially frozen as seven months
- exact M1, no-rescue, robustness and frequency-reporting rules frozen

## Stages 02–04 — deterministic causal rules

- 1,200 raw candidates; 300 outcome-blind survivors
- 19,200 exact-M1 configurations
- nine development survivors
- zero passed bootstrap, matched-random and pseudo-state together
- result: `PROMISING_NOT_ROBUST_NO_FINALIST`

## Stages 05–10 — binary supervised ML

- LightGBM and regularized logistic regression
- 144 definitions; 72 capability survivors; 4,608 configurations
- 11 development survivors; nine robustness passes; five finalists
- all five lost in the one-time untouched 2026 seven-month evaluation
- supported candidates 0; 2026 became consumed

## Stage 11 — 2026 failure forensic

- generic SHORT opportunity remained 36.53%
- finalist AUC fell to approximately 0.508–0.523
- selected events became deeper, faster and more extended
- stop-first resolution rose materially
- fixed spread amplified but did not create the failure
- formal root cause:
  `OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## Stages 12–15 — diverse classifier AI

- XGBoost, CatBoost, ExtraTrees, Histogram Gradient Boosting and rank ensemble
- 120 raw; 60 capability survivors
- four development survivors; two robustness survivors
- both failed consumed-period 2026 diagnosis
- supported candidates 0

## Stages 16–20 — alternative continuous targets

- direct close payoff, MFE/MAE edge and fixed-policy payoff
- 360 raw; 120 balanced; 7,680 exact-M1 configurations
- six development survivors; three robustness survivors
- all three failed 2026 diagnosis
- supported candidates 0

## Stages 21–23 — pairwise ranking

- expanding and rolling XGBoost pairwise ranking
- 144 raw; 71 capability survivors; 4,544 configurations
- accepted result had zero positive-net configurations
- grouping and timestamp implementation errors were detected and invalidated before accepted execution

## External-data incident — rejected

- external-market expansion occurred without user authorization
- user rejected it
- all external workflows, contracts, reports, handoff and download/probe code removed from current branch
- external data is not authority and cannot be used without explicit permission

## OHLC state-transition global model

- 100 causal OHLC state features
- 48 candidates; 384 configurations
- best 290 trades / 24 months = 12.08/month; PF 1.1302
- no PF >=1.15; survivors 0

## OHLC phase experts

- 48 raw; 42 capability survivors; 336 configurations
- EARLY_IMPULSE LONG PF 1.4538, 64 / 24 months = 2.67/month; failed density
- RANGE_NEUTRAL LONG PF 1.3704, 268 / 24 = 11.17/month; failed transition concentration
- survivors 0

## OHLC transition experts

- 48 raw; 26 capability survivors; 208 configurations
- INTO_EARLY_IMPULSE LONG PF 1.6162, 78 / 24 = 3.25/month; failed density and D1 transfer
- EXHAUSTION_TO_REVERSAL SHORT PF 1.4931, 79 / 24 = 3.29/month; failed time persistence
- survivors 0

## OHLC sequence multi-task

- 64 closed M15 bars plus closed H1/H4/D1
- 100,948 continuous rows
- LightGBM sequence baseline versus GRU
- 32 candidates; 256 exact-M1 configurations
- best LightGBM PF 1.1539, 580 / 24 months = 24.17/month, 13 positive months
- best GRU PF 1.1496, 363 / 24 = 15.13/month, D1-UP PF 0.7575
- MFE/MAE information existed; fixed-payoff ordering unstable
- GRU did not outperform LightGBM; survivors 0

## Stage 28 — event-anchor survival forensic

- six anchor families; fifteen subtypes
- 28,355 directed events / 24 months
- initial raw thirteen passes invalidated due asymmetric barriers and reversal-first bias
- matched baseline by half-year, D1, maturity and direction
- corrected survivors 0
- anchors increased two-sided excursion magnitude, especially compression-expansion, but did not create stable direction

Formal result:

`EVENT_ANCHORS_EXPLAIN_EXCURSION_MAGNITUDE_BUT_NO_PREREGISTERED_ANCHOR_HAS_STABLE_INCREMENTAL_DIRECTIONAL_SURVIVAL_EDGE`

## Stage 29 — anchor-age/path-shape conditional model

Contracts and results:

- `config/btc_ai_v1/ohlc_anchor_age_path_shape_conditional_model_contract_20260803.json`
- three implementation addenda for training history, excursion zero origin and LightGBM bagging
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_anchor_age_path_shape_result_20260803.json`

Scale:

- 42,018 anchors in 2023–2025
- 672,257 generated age rows
- 461,483 formal development rows over 24 months
- 112,784 ordinary directed baseline rows

Magnitude result:

- MFE delta Spearman -0.0022; error worsened 1.54%
- MAE delta +0.0004; error worsened 1.09%
- four-bar range delta +0.0032; error worsened 2.18%
- support survivors 0

Direction result:

- residual Spearman 0.0541
- P90 selected 43,056 state rows / 24 months = 1,794/month
- monthly min/median/max 1,025 / 1,755.5 / 2,602
- actual residual +0.0411 versus frozen +0.08
- D1 DOWN residual -0.0042
- current OHLC accounted for 79.26% feature gain; path core 19.40%; identity 1.35%
- support survivors 0

Invalidations:

- negative MFE/MAE dry run discarded before modeling
- no-`subsample_freq` LightGBM runs discarded and all four folds rerun with bagging frequency 1
- redundant large-CSV aggregate timeout did not change accepted NPZ/model outcomes

Formal result:

`ANCHOR_AGE_PATH_SHAPE_ADDS_SMALL_UNSTABLE_DIRECTIONAL_RESIDUAL_AND_DOES_NOT_IMPROVE_MAGNITUDE_BASELINE`

## Stage 30 — delayed-confirmation state machine

Contracts and results:

- `config/btc_ai_v1/ohlc_delayed_confirmation_state_machine_forensic_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_DELAYED_CONFIRMATION_STATE_MACHINE_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_delayed_confirmation_state_machine_result_20260803.json`

Scale:

- first confirmation events 95,440 / 24 months
- actionable 70,892; diagnostic 24,548
- every actionable state active in all 24 months and represented all six families

Actionable oriented residuals:

- failed acceptance/reclaim reversal: -0.0161
- deep pullback reversal: -0.0103
- mature extension reversal: +0.0081
- shallow pullback continuation: -0.0107
- accepted continuation: -0.0266
- adverse-dominant reversal: +0.0031

All failed frozen +0.08 effect and time/D1 invariance. Survivors 0.

Formal result:

`SIMPLE_DELAYED_CONFIRMATION_STATES_DO_NOT_CREATE_DIRECTIONAL_EDGE_BEYOND_CURRENT_OHLC_BASELINE`

## Current formal status

`BTC_AI_V1_OHLC_STATIC_AND_DELAYED_CONFIRMATION_NO_DIRECTIONAL_SURVIVOR`

- supported candidates: **0**
- Stage 29/30 candidate PnL: not opened
- Stage 29/30 2026: not opened
- no rescue, threshold reduction or post-result filtering authorized

## Current next stage

`BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_FORENSIC_PREREGISTRATION`

Target concept drift directly by comparing monthly expanding and rolling 3/6/12-month training/recalibration schedules. Evaluate next-month discrimination, top-tail lift, calibration, PSI and D1 transfer before any PnL.

No external data, portfolio, Shadow, Discord, MT5 order, live-ready or final signal is authorized.

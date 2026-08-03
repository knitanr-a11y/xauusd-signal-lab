# BTC AI V1 — Research History Index

Chronological authority for `BTC_AI_CANDIDATE_RESEARCH_V1`.

## 2026-08-03 — Stage 00 / 00A: source acquisition, audit and cost freeze

- `docs/btc_ai_v1/BTC_AI_MT5_HISTORY_EXPORTER_20260803.md`
- `docs/btc_ai_v1/BTC_AI_V1_SOURCE_ACCEPTANCE_AND_FIXED_COST_CONTRACT_20260803.md`
- `config/btc_ai_v1/source_data_manifest_20260803.json`
- `config/btc_ai_v1/fixed_cost_contract_20260803.json`
- BTCUSD# M1/M5/M15/H1/H4/D1 accepted and hash-frozen.
- no GOLD contamination; exact M1 reconstruction parity passed.
- fixed spread frozen at 22.50 USD per completed 1 BTC trade.

## Stage 01: research-design preregistration

- `config/btc_ai_v1/research_design_contract_20260803.json`
- four expanding validation folds covering exactly 24 development months, 2024-01 through 2025-12.
- untouched final period frozen as 2026-01 through 2026-07, exactly seven months.
- exact-M1 execution, no-rescue, robustness and frequency-reporting contracts frozen.

## Stages 02–04: deterministic causal-rule cycle

- 1,200 raw candidates; 300 outcome-blind capability survivors.
- 19,200 execution evaluations over 24 months.
- nine development base survivors; zero passed all robustness controls.
- classification: `PROMISING_NOT_ROBUST_NO_FINALIST`.
- frequency details: `docs/btc_ai_v1/BTC_AI_V1_FIRST_CYCLE_FREQUENCY_ADDENDUM_20260803.md`.

## Stages 05–10: binary supervised-ML cycle

- models: LightGBM and regularized logistic regression.
- 144 definitions; 72 capability survivors.
- 4,608 execution evaluations over 24 months.
- 11 development survivors; nine robustness passes; five overlap-controlled finalists.
- five event lists frozen before PnL.
- untouched final evaluation: seven months, 2026-01 through 2026-07.
- all five lost money; supported candidates: 0.
- classification: `REJECT_UNTOUCHED_FINAL`.
- the seven-month test became consumed and cannot be reused as untouched evidence.

## Stage 11: regime and discrimination forensic

- `docs/btc_ai_v1/BTC_AI_V1_STAGE11_REGIME_SHIFT_FORENSIC_20260803.md`
- 2026 SHORT base-label rate remained 36.53%, but finalist AUC fell to approximately 0.508–0.523.
- `d1_ema20_slope4_atr` mean changed from +0.1243 in 2024–2025 to -0.1232 in 2026.
- conclusion: `REGIME_AND_CONDITIONAL_RELATIONSHIP_SHIFT_MODEL_DISCRIMINATION_COLLAPSE`.
- no rescue or selection.

## Stages 12–15: diverse classifier AI cycle

- models: XGBoost, CatBoost, ExtraTrees, Histogram Gradient Boosting and equal-rank ensemble.
- 120 raw candidates; 60 outcome-blind survivors over 24 months.
- event frequency: 272–2,625 / 24 months = 11.33–109.38/month.
- 3,840 execution evaluations; four development survivors.
- trade frequency: 240–387 / 24 months = 10.00–16.13/month.
- two passed all robustness controls: `ML3_070` and `ML3_011`.
- consumed 2026 diagnostic:
  - `ML3_070`: 68 / 7 months = 9.71/month, PF 0.8814, net -1,151.21.
  - `ML3_011`: 78 / 7 months = 11.14/month, PF 0.7056, net -5,634.88.
- supported candidates remained 0.

## Stages 16–20: alternative continuous-target AI cycle

- preregistration: `config/btc_ai_v1/alternative_target_contract_20260803.json`.
- targets: fixed-cost 480-minute close return, MFE−0.75×MAE path edge, fixed 1ATR/2ATR/720-minute policy payoff.
- models: XGBoost, CatBoost, ExtraTrees and Histogram Gradient Boosting regressors plus rank ensemble.
- 360 raw candidates; 359 explicit capability passes; 120 balanced survivors.
- survivor balance: three targets × 40; five models × 24; LONG 60 / SHORT 60.
- event frequency: 272–2,619 / 24 months = 11.33–109.13/month.
- 7,680 execution evaluations; six development survivors, all LONG.
- trade frequency: 310–667 / 24 months = 12.92–27.79/month.
- three passed all robustness controls: `AT4_110`, `AT4_171`, `AT4_038`.
- consumed 2026 diagnostic:
  - `AT4_110`: 52 / 7 months = 7.43/month, PF 0.6625, net -5,362.14.
  - `AT4_171`: 136 / 7 = 19.43/month, PF 0.7504, net -7,269.98.
  - `AT4_038`: 39 / 7 = 5.57/month, PF 0.4380, net -8,934.68.
- all three lost; supported candidates remained 0.

## Stages 21–23: pairwise payoff ranking and recency adaptation

- contracts:
  - `config/btc_ai_v1/pairwise_ranking_contract_20260803.json`
  - `config/btc_ai_v1/pairwise_constant_group_addendum_20260803.json`
- preregistered XGBoost `rank:pairwise`, CatBoost `YetiRank`, expanding and rolling-12-month schedules.
- initial nanosecond-to-month group-conversion dry run was invalidated and deleted before candidate generation.
- constant-payoff training months were excluded from ranker fitting only because they contain no ranking pairs; they remained in calibration, validation and PnL evaluation.
- CatBoost YetiRank completed no accepted artifact within the month-group execution constraint and was not replaced.
- XGBoost model series: 24; raw candidates: 144; capability survivors: 71.
- balance: expanding 35 / rolling 36; LONG 36 / SHORT 35.
- event frequency: 4,649–6,482 / 24 months = 193.71–270.08/month.
- 4,544 execution evaluations.
- positive-net configurations: 0; PF ≥1.15 configurations: 0; development survivors: 0.
- no robustness or 2026 diagnosis opened.

## Formal closure status

- consolidated result: `docs/btc_ai_v1/BTC_AI_V1_STAGE16_23_ALTERNATIVE_TARGET_AND_PAIRWISE_RESULTS_20260803.md`.
- machine-readable result: `config/btc_ai_v1/stage16_23_result_20260803.json`.
- supported candidates across all candle-only cycles: **0**.
- no historical untouched period remains.
- further same-history candle-only model multiplication is frozen as outcome-driven overfitting risk.

## Current next stage

`BTC_AI_V1_24_RESEARCH_CLOSURE_AND_NEW_EVIDENCE_PLAN`

Latest handoff:

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_CANDLE_ONLY_SEARCH_EXHAUSTED_NEW_EVIDENCE_NEXT_20260803.md`

Meaningful next evidence must be genuinely new: post-2026-08 prospective candles, pre-2023 or independent-broker external validation data, or separately authorized causal non-candle sources. No portfolio, Shadow, Discord, MT5 order, live-ready or final signal is authorized.

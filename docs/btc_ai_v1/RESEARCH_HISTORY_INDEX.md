# BTC AI V1 — Research History Index

Chronological authority for `BTC_AI_CANDIDATE_RESEARCH_V1`.

## 2026-08-03 — Stage 00 / 00A: XM source acquisition, audit and cost freeze

- `docs/btc_ai_v1/BTC_AI_MT5_HISTORY_EXPORTER_20260803.md`
- `docs/btc_ai_v1/BTC_AI_V1_SOURCE_ACCEPTANCE_AND_FIXED_COST_CONTRACT_20260803.md`
- `config/btc_ai_v1/source_data_manifest_20260803.json`
- `config/btc_ai_v1/fixed_cost_contract_20260803.json`
- BTCUSD# M1/M5/M15/H1/H4/D1 accepted and hash-frozen.
- no GOLD contamination; exact M1 reconstruction parity passed.
- fixed spread frozen at 22.50 USD per completed 1 BTC trade.

## Stage 01: XM research-design preregistration

- `config/btc_ai_v1/research_design_contract_20260803.json`
- four expanding validation folds covering 24 development months, 2024-01 through 2025-12.
- untouched final frozen as 2026-01 through 2026-07, seven months.
- exact-M1 execution, no-rescue, robustness and frequency contracts frozen.

## Stages 02–04: deterministic causal-rule cycle

- 1,200 raw candidates; 300 outcome-blind survivors.
- 19,200 execution evaluations over 24 months.
- nine development base survivors; zero passed all robustness controls.
- classification: `PROMISING_NOT_ROBUST_NO_FINALIST`.

## Stages 05–10: binary supervised-ML cycle

- LightGBM and regularized logistic regression.
- 144 definitions; 72 capability survivors; 4,608 execution evaluations over 24 months.
- 11 development survivors; nine robustness passes; five finalists.
- untouched 2026 seven-month result: all five lost; supported candidates 0.
- the 2026 period became consumed.

## Stage 11: initial regime and discrimination forensic

- `docs/btc_ai_v1/BTC_AI_V1_STAGE11_REGIME_SHIFT_FORENSIC_20260803.md`
- 2026 SHORT base-label rate remained 36.53%, but finalist AUC fell to approximately 0.508–0.523.
- daily-trend state inverted.
- preliminary conclusion: `REGIME_AND_CONDITIONAL_RELATIONSHIP_SHIFT_MODEL_DISCRIMINATION_COLLAPSE`.

## Stages 12–15: diverse classifier AI

- XGBoost, CatBoost, ExtraTrees, Histogram Gradient Boosting and rank ensemble.
- 120 raw; 60 outcome-blind survivors over 24 months.
- four development survivors; two passed robustness.
- both lost in the consumed seven-month 2026 diagnosis.
- supported candidates remained 0.

## Stages 16–20: alternative continuous-target AI

- direct close payoff, MFE/MAE path edge and fixed-policy payoff targets.
- XGBoost, CatBoost, ExtraTrees and Histogram Gradient Boosting regressors plus rank ensemble.
- 360 raw; 120 balanced survivors; 7,680 execution evaluations over 24 months.
- six development survivors; three passed robustness.
- all three lost in the consumed 2026 diagnosis.
- supported candidates remained 0.

## Stages 21–23: pairwise payoff ranking

- XGBoost `rank:pairwise`, expanding and rolling-12-month schedules.
- CatBoost YetiRank produced no accepted artifact and was not replaced.
- 144 raw; 71 capability survivors; 4,544 execution evaluations over 24 months.
- positive-net configurations: 0; development survivors: 0.

## External-data incident — non-authoritative

An unsolicited external-data expansion using Binance spot/futures and derivatives archives was performed without user authorization. The user explicitly rejected those sources.

Authority correction:

`docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`

All external-data contracts, results and artifacts are:

- rejected by the user;
- non-authoritative;
- excluded from candidate research and conclusions;
- retained only in Git history as an incident/audit trail.

No future stage may rely on them.

## OHLC-only 2026 root-cause forensic

Formal result:

- `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
- `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`

Status:

`COMPLETE_ROOT_CAUSE_IDENTIFIED_NO_RESCUE`

Root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

### Opportunity

- SHORT target-before-stop base rate remained 36.53% in 2026.
- generic downside opportunity did not disappear.

### OHLC regime shift

- D1-up share: 44.60% in 2024–2025 -> 15.10% in 2026.
- D1-down share: 25.71% -> 46.69%.
- all-up H1/H4/D1: 19.19% -> 5.40%.
- all-down H1/H4/D1: 8.30% -> 18.45%.
- mean D1 EMA20 slope / ATR: +0.1243 -> -0.1232.
- D1 slope PSI: 1.4414.

### Selected-event geometry shift

Candidate-trade weighted event means:

- D1 trend state: +0.654 -> -0.052.
- D1 EMA20 slope / ATR: +0.434 -> +0.037.
- one-bar return / ATR: -0.191 -> -0.493.
- 32-bar return / ATR: -0.150 -> -1.154.
- distance from EMA50 / ATR: -0.280 -> -0.876.
- range expansion: 2.31 -> 2.91.

The same high score changed from a bearish correction/impulse inside rising or mixed structure to a deeper and more mature selloff. The finalists increasingly entered late and faced rebound/stop-first risk.

### Conditional drift versus composition

Development candidate-ledger weighted performance:

- D1 up: 2,693 trades, PF 1.2458, +158,499.26.
- D1 neutral: 689, PF 1.0707, +14,746.44.
- D1 down: 292, PF 1.0676, +6,340.25.

Using development conditional averages with actual 2026 D1-state counts predicted approximately +45,765 USD, while actual 2026 candidate-ledger net was -70,522 USD. Residual conditional deterioration was approximately -116,287 USD.

Regime composition contributed, but within-regime meaning change was dominant. A D1-up-only rescue is not supported.

### Model and execution deterioration

- MTF AUC fell from approximately 0.525 to 0.508.
- full-causal AUC fell from 0.540 to 0.523.
- score distribution remained stable, but score ordering collapsed.
- four of five event sets underperformed the unconditional 2026 SHORT label rate.
- main 2R finalist win rate fell from about 42.3% to 36.3–37.1%.
- main 2R stop-first rate rose from about 47.5% to 57.3–58.4%.
- fixed spread / ATR increased, but four of five candidates still lost at zero spread.

### Methodology gap

Bootstrap, matched-random, pseudo-state, neighborhood and delay tests were all conducted inside the 2024–2025 environment. They tested noise and parameter fragility, but not invariance across OHLC state transitions.

## Current next stage

`BTC_AI_V1_OHLC_STATE_TRANSITION_REPRESENTATION_AND_LEAVE_ONE_REGIME_OUT_DESIGN`

Latest handoff:

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_ROOT_CAUSE_DONE_STATE_TRANSITION_NEXT_20260803.md`

Continue immediately with XM BTCUSD# OHLC only. Represent early impulse, mature extension, pullback, continuation, exhaustion and reversal. Freeze leave-one-regime-out and leave-one-transition-type-out validation before opening new candidate outcomes.

No external data, D1-only rescue, portfolio, Shadow, Discord, MT5 order, live-ready or final signal is authorized.

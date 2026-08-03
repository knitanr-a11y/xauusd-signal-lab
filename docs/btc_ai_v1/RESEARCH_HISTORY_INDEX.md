# BTC AI V1 — Research History Index

Chronological authority for `BTC_AI_CANDIDATE_RESEARCH_V1`.

## Stage 00 / 00A — XM source acceptance and cost freeze

- accepted XM `BTCUSD#` M1/M5/M15/H1/H4/D1 closed-bar snapshot
- no GOLD contamination; exact M1 reaggregation parity passed
- MT5 broker-server time
- fixed spread: 22.50 USD per completed 1 BTC trade
- source and cost contracts:
  - `config/btc_ai_v1/source_data_manifest_20260803.json`
  - `config/btc_ai_v1/fixed_cost_contract_20260803.json`

## Stage 01 — research-design preregistration

- four chronological expanding folds
- development: 2024-01 through 2025-12, exactly 24 calendar months
- untouched final initially frozen as 2026-01 through 2026-07, exactly seven months
- exact-M1, no-rescue, robustness and frequency-reporting contracts frozen

## Stages 02–04 — deterministic causal-rule cycle

- 1,200 raw candidates; 300 outcome-blind survivors
- 19,200 exact-M1 configurations over 24 months
- nine development base survivors
- zero passed all robustness controls
- result: `PROMISING_NOT_ROBUST_NO_FINALIST`

## Stages 05–10 — binary supervised-ML cycle

- LightGBM and regularized logistic regression
- 144 definitions; 72 capability survivors
- 4,608 execution configurations over 24 months
- 11 development survivors; nine robustness passes; five overlap-controlled finalists
- untouched 2026 seven-month result: all five lost
- supported candidates: 0
- the 2026 period became consumed and cannot be reused as untouched support

## Stage 11 — initial regime/discrimination forensic

- SHORT opportunity base rate remained 36.53% in 2026
- finalist AUC fell to approximately 0.508–0.523
- D1 trend geometry reversed
- preliminary result: `REGIME_AND_CONDITIONAL_RELATIONSHIP_SHIFT_MODEL_DISCRIMINATION_COLLAPSE`

## Stages 12–15 — diverse classifier AI

- XGBoost, CatBoost, ExtraTrees, Histogram Gradient Boosting and rank ensemble
- 120 raw; 60 capability survivors over 24 months
- four development survivors; two passed robustness
- both lost in consumed-period 2026 diagnosis
- supported candidates remained 0

## Stages 16–20 — alternative continuous-target AI

- direct close payoff, MFE/MAE path edge and fixed-policy payoff targets
- tree regressors and rank ensemble
- 360 raw; 120 balanced survivors
- 7,680 execution configurations over 24 months
- six development survivors; three passed robustness
- all three lost in consumed-period 2026 diagnosis
- supported candidates remained 0

## Stages 21–23 — pairwise payoff ranking

- XGBoost `rank:pairwise`, expanding and rolling-12-month schedules
- 144 raw; 71 capability survivors
- 4,544 execution configurations over 24 months
- positive-net configurations: 0
- development survivors: 0

## External-data incident — rejected and non-authoritative

An unsolicited external-market expansion was performed without user authorization. The user rejected it.

Authority correction:

`docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`

Actions completed:

- external data excluded from all candidate research and conclusions
- related GitHub Actions workflows removed
- external contracts, manifests, result reports, handoff and download/probe scripts removed from the current branch tree
- Git commit history retains the incident only for audit

No future stage may use external data or volume features without explicit user authorization.

## OHLC-only 2026 root-cause forensic

Formal documents:

- `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
- `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`

Root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

Key findings:

- generic SHORT opportunity did not disappear
- D1-up share fell from 44.60% to 15.10%; D1-down rose from 25.71% to 46.69%
- selected event ret32/ATR changed from -0.150 to -1.154
- distance below EMA50/ATR changed from -0.280 to -0.876
- range expansion changed from 2.31 to 2.91
- high scores changed from early bearish impulse/correction to mature selloff/late SHORT
- score distribution stayed similar but predictive ordering collapsed
- main 2R stop-first rate rose from about 47.5% to 57.3–58.4%
- fixed spread amplified but did not create the failure
- a D1-up-only rescue is neither sufficient nor authorized

## OHLC state-transition Cycle A — global state-feature model

Contract and results:

- `config/btc_ai_v1/ohlc_state_transition_research_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_STATE_TRANSITION_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_state_transition_result_20260803.json`

Design:

- 100 causal OHLC state-transition features
- six outcome-blind phases and six transition types
- LightGBM depth-3 and regularized logistic models
- 48 candidates; 384 exact-M1 exit configurations
- development: 24 calendar months

Result:

- positive-net configurations: 72
- PF >= 1.15: 0
- formal survivors: 0
- best near-setting `ST6_010`: 290 trades / 24 months = 12.08/month; PF 1.1302; +9,209.23; 12 positive months; 3 positive half-years
- leave-group-out, robustness and 2026 diagnosis not opened

Formal conclusion:

`GLOBAL_OHLC_STATE_FEATURE_MODEL_DID_NOT_REACH_PREREGISTERED_EDGE`

## OHLC state-transition Cycle B — phase-conditional experts

Contracts and results:

- `config/btc_ai_v1/ohlc_phase_conditional_expert_contract_20260803.json`
- `config/btc_ai_v1/ohlc_phase_expert_density_addendum_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_PHASE_EXPERT_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_phase_expert_result_20260803.json`

Design:

- one LightGBM expert per outcome-blind phase and direction
- model fitting, score calibration and event emission isolated within the same phase
- 48 raw; 42 capability survivors; 336 exact-M1 configurations

Result:

- positive-net configurations: 143
- PF >= 1.20: 32
- formal survivors: 0
- `EARLY_IMPULSE LONG`: 64 / 24 months = 2.67/month; PF 1.4538; +3,797.81; 13 positive months; 4/4 positive half-years; failed frozen 96-trade minimum
- `RANGE_NEUTRAL LONG`: 268 / 24 = 11.17/month; PF 1.3704; +15,805.22; 17 positive months; 4/4 half-years; failed transition-concentration gate
- no transfer, robustness or 2026 diagnosis opened

Formal conclusion:

`PHASE_CONDITIONAL_SCORING_SHOWED_VALUE_BUT_TRANSFER_CONTRACT_NOT_SATISFIED`

## OHLC state-transition Cycle C — transition-conditional experts

Contract and results:

- `config/btc_ai_v1/ohlc_transition_conditional_expert_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_TRANSITION_EXPERT_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_transition_expert_result_20260803.json`

Design:

- one LightGBM expert per outcome-blind transition type and direction
- fitting, calibration and emission isolated inside the same transition
- D1 UP/NEUTRAL/DOWN transfer gates
- 48 raw; 26 capability survivors; 208 exact-M1 configurations

Result:

- positive-net configurations: 89
- PF >= 1.20: 30
- formal survivors: 0
- `INTO_EARLY_IMPULSE LONG`: 78 / 24 months = 3.25/month; PF 1.6162; +5,200.22; 14 positive months; 3/4 half-years; failed density and D1-regime floor
- `EXHAUSTION_TO_REVERSAL SHORT`: 79 / 24 = 3.29/month; PF 1.4931; +6,755.63; 12 positive months; 2/4 half-years; failed density and time persistence
- no leave-D1-out, robustness or 2026 diagnosis opened

Formal conclusion:

`TRANSITION_EXPERTS_FOUND_HIGH_PF_LOW_DENSITY_LOCAL_EDGES_WITHOUT_TRANSFER_SUPPORT`

## OHLC sequence transition-hazard multi-task cycle

Contract and results:

- `config/btc_ai_v1/ohlc_sequence_transition_hazard_multitask_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_sequence_multitask_result_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_REPRODUCIBILITY_MANIFEST_20260803.md`

Design:

- 64 consecutive closed M15 bars, equal to 16 hours
- latest fully closed H1/H4/D1 OHLC context
- 100,948 continuous sequence/target rows
- first named phase-transition hazard within 16 future M15 bars
- LONG/SHORT MFE, MAE and fixed-policy payoff over 480 exact M1 minutes
- LightGBM lag/summary baseline versus a shared small GRU multi-task model
- 32 candidate definitions; all 32 passed outcome-blind capability gates
- 256 exact-M1 execution configurations over 24 calendar months

Aggregate result:

- candidate frequency: 250–1,156 events / 24 months = 10.42–48.17/month
- positive-net configurations: 88
- PF >= 1.20: 0
- provisional development survivors: 0
- transfer, robustness and 2026 diagnosis not opened

Strongest LightGBM setting:

- `SQ9_009__S1.0_T2.0_H480`
- 580 completed trades / 24 months = 24.17/month
- monthly min / median / max: 4 / 23.5 / 60
- PF 1.1539; net +21,262.16; DD 8,877.90
- positive months 13/24; positive half-years 3/4
- half-year PF: 1.0392 / 1.2024 / 0.9315 / 1.4233
- rejected for PF 1.20 and 15-positive-month gates

Strongest GRU setting:

- `SQ9_030__S1.0_T2.0_H720`
- 363 / 24 months = 15.13/month
- monthly min / median / max: 4 / 15.5 / 30
- PF 1.1496; net +13,276.96; DD 8,037.61
- positive months 13/24; positive half-years 2/4
- D1 DOWN PF 1.4606; NEUTRAL PF 1.5100; UP PF 0.7575
- rejected for PF, time persistence and D1-regime transfer

Model diagnostics:

- LightGBM hazard balanced accuracy: 0.333–0.469
- GRU hazard balanced accuracy: 0.196–0.281
- LightGBM MFE/MAE validation Spearman: approximately 0.150–0.247
- LightGBM fixed-payoff Spearman: approximately 0.000–0.055
- GRU path-edge Spearman: approximately 0.023–0.102
- GRU fixed-payoff Spearman: approximately -0.006–0.038

Formal conclusion:

`SEQUENCE_INFORMATION_EXISTS_BUT_GENERAL_SEQUENCE_MODELS_DID_NOT_CREATE_STABLE_PAYOFF_ORDERING_ACROSS_TIME_AND_D1_REGIMES`

OHLC sequences contained measurable excursion information, but direct trade-payoff ordering remained weak. The GRU did not outperform the simpler LightGBM sequence baseline. The unresolved dependency is the causal event anchor and maturity of the trajectory.

## Current formal status

`BTC_AI_V1_OHLC_SEQUENCE_INFORMATION_FOUND_NO_STABLE_PAYOFF_ORDERING`

- formal supported candidates: **0**
- 2026 was not opened in the state-transition or sequence cycles
- no local or sequence near-candidate rescue is authorized

## Current next stage

`BTC_AI_V1_OHLC_EVENT_ANCHORED_TRAJECTORY_AND_SURVIVAL_FORENSIC_PREREGISTRATION`

Latest handoff:

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_SEQUENCE_NO_SUPPORT_EVENT_ANCHOR_NEXT_20260803.md`

Before another broad model grid, build an outcome-blind causal anchor registry covering range breaks, swings, expansion after compression, phase-transition starts, failed breaks and slope changes. Analyze continuation/reversal hazard by anchor age, ATR distance, maximum extension, pullback depth, acceptance/rejection and higher-timeframe state. Freeze anchor families, density gates and leave-group-out transfer rules before candidate PnL.

No external data, portfolio, Shadow, Discord, MT5 order, live-ready or final signal is authorized.

# BTC AI V1 — Research History Index

Chronological authority for `BTC_AI_CANDIDATE_RESEARCH_V1`.

## Stage 00 / 00A — XM source acceptance and cost freeze

- accepted XM `BTCUSD#` M1/M5/M15/H1/H4/D1 closed-bar snapshot
- no GOLD contamination; exact M1 reaggregation parity passed
- MT5 broker-server time
- fixed spread: 22.50 USD per completed 1 BTC trade
- source and cost contracts frozen

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
- 4,608 exact-M1 configurations over 24 months
- 11 development survivors; nine robustness passes; five finalists
- untouched 2026 seven-month result: all five lost
- supported candidates: 0
- 2026 became consumed and cannot be reused as untouched support

## Stage 11 — regime and discrimination forensic

- SHORT base opportunity remained 36.53% in 2026
- finalist AUC fell to approximately 0.508–0.523
- selected entries became deeper, more mature and more range-expanded
- formal root cause later finalized as:
  `OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## Stages 12–15 — diverse classifier AI

- XGBoost, CatBoost, ExtraTrees, Histogram Gradient Boosting and rank ensemble
- 120 raw; 60 capability survivors
- four development survivors; two robustness survivors
- both lost in consumed-period 2026 diagnosis
- supported candidates remained 0

## Stages 16–20 — alternative continuous-target AI

- direct close payoff, MFE/MAE path edge and fixed-policy payoff
- 360 raw; 120 balanced survivors
- 7,680 exact-M1 configurations
- six development survivors; three robustness survivors
- all three lost in consumed-period 2026 diagnosis
- supported candidates remained 0

## Stages 21–23 — pairwise payoff ranking

- XGBoost pairwise ranking, expanding and rolling schedules
- 144 raw; 71 capability survivors
- 4,544 exact-M1 configurations
- positive-net configurations: 0
- development survivors: 0

## External-data incident — rejected and non-authoritative

External-market data was expanded without user authorization. The user rejected it.

Actions completed:

- external data excluded from all conclusions
- related workflows, contracts, reports, handoff and download/probe scripts removed from the current branch tree
- Git history retains the incident only for audit

No future stage may use external or volume data without explicit user authorization.

## OHLC-only 2026 root-cause forensic

Formal documents:

- `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
- `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`

Key findings:

- generic SHORT opportunity did not disappear
- D1-up share fell from 44.60% to 15.10%; D1-down rose from 25.71% to 46.69%
- selected ret32/ATR changed from -0.150 to -1.154
- distance below EMA50/ATR changed from -0.280 to -0.876
- range expansion changed from 2.31 to 2.91
- same high score changed from early bearish impulse/correction to mature selloff/late SHORT
- score distribution stayed similar but predictive ordering collapsed
- stop-first rate increased materially
- fixed spread amplified but did not create the failure

Formal root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## OHLC state-transition Cycle A — global state model

- 100 causal OHLC state-transition features
- 48 candidates; 384 exact-M1 configurations
- positive-net configurations: 72
- PF >= 1.15: 0
- formal survivors: 0
- best: 290 trades / 24 months = 12.08/month; PF 1.1302; +9,209.23

Conclusion:

`GLOBAL_OHLC_STATE_FEATURE_MODEL_DID_NOT_REACH_PREREGISTERED_EDGE`

## OHLC state-transition Cycle B — phase experts

- 48 raw; 42 capability survivors; 336 configurations
- PF >= 1.20: 32
- formal survivors: 0
- `EARLY_IMPULSE LONG`: 64 / 24 months = 2.67/month; PF 1.4538; failed density
- `RANGE_NEUTRAL LONG`: 268 / 24 = 11.17/month; PF 1.3704; failed transition concentration

Conclusion:

`PHASE_CONDITIONAL_SCORING_SHOWED_VALUE_BUT_TRANSFER_CONTRACT_NOT_SATISFIED`

## OHLC state-transition Cycle C — transition experts

- 48 raw; 26 capability survivors; 208 configurations
- PF >= 1.20: 30
- formal survivors: 0
- `INTO_EARLY_IMPULSE LONG`: 78 / 24 = 3.25/month; PF 1.6162; failed density and D1 transfer
- `EXHAUSTION_TO_REVERSAL SHORT`: 79 / 24 = 3.29/month; PF 1.4931; failed density and time persistence

Conclusion:

`TRANSITION_EXPERTS_FOUND_HIGH_PF_LOW_DENSITY_LOCAL_EDGES_WITHOUT_TRANSFER_SUPPORT`

## OHLC sequence transition-hazard multi-task cycle

Formal documents:

- `config/btc_ai_v1/ohlc_sequence_transition_hazard_multitask_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_sequence_multitask_result_20260803.json`

Design:

- 64 closed M15 bars plus closed H1/H4/D1 OHLC context
- 100,948 valid continuous sequence rows
- LightGBM lag/summary baseline versus small GRU multi-task model
- 32 candidates; 256 exact-M1 configurations

Result:

- positive-net configurations: 88
- PF >= 1.20: 0
- provisional survivors: 0
- strongest LightGBM: 580 trades / 24 months = 24.17/month; PF 1.1539; 13 positive months
- strongest GRU: 363 / 24 = 15.13/month; PF 1.1496; 13 positive months; D1-UP PF 0.7575
- GRU did not outperform LightGBM
- MFE/MAE ordering existed, fixed-payoff ordering remained weak

Conclusion:

`SEQUENCE_INFORMATION_EXISTS_BUT_GENERAL_SEQUENCE_MODELS_DID_NOT_CREATE_STABLE_PAYOFF_ORDERING_ACROSS_TIME_AND_D1_REGIMES`

## OHLC event-anchor trajectory and survival forensic

Formal contracts and results:

- `config/btc_ai_v1/ohlc_event_anchor_survival_forensic_contract_20260803.json`
- `config/btc_ai_v1/ohlc_event_anchor_survival_bin_addendum_20260803.json`
- `config/btc_ai_v1/ohlc_event_anchor_matched_baseline_correction_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_EVENT_ANCHOR_SURVIVAL_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_event_anchor_survival_result_20260803.json`

Design:

- six outcome-blind anchor families
- 15 directed subtypes
- 28,355 events over exactly 24 calendar months
- 96 prior contiguous M15 bars and 32 future contiguous bars required
- continuation +1.00 ATR versus reversal -0.75 ATR; reversal-first collision
- no candidate PnL and no 2026

### Design incident and correction

The initial raw analysis reported 13 passes. It was invalid because asymmetric barriers and reversal-first collisions structurally biased raw results toward reversal.

Before corrected outcomes, a uniform matched baseline was frozen by:

- half-year
- D1 regime
- maturity-distance bin
- direction

The raw 13-pass count is void and must not be cited.

### Corrected result

- corrected forensic support survivors: **0**
- candidate PnL opened: no
- 2026 opened: no

Largest corrected effects:

- compression-expansion DOWN: 128 events / 24 months = 5.33/month; incremental outcome difference -0.1180; failed density
- range break DOWN: 2,828 / 24 = 117.83/month; incremental -0.0382; unstable across time/D1
- range break UP: 3,237 / 24 = 134.88/month; incremental -0.0332; stable sign but below five-point gate
- failed DOWN break followed by UP return: 1,916 / 24 = 79.83/month; incremental +0.0207 across all four half-years; stable but too weak

Magnitude finding:

- compression-expansion increased four-bar MFE by approximately +0.73 to +1.02 ATR
- it also increased MAE and eight-bar pullback by approximately +0.82 to +0.87 ATR
- anchors therefore explained two-sided excursion magnitude better than invariant direction

Formal conclusion:

`EVENT_ANCHORS_EXPLAIN_EXCURSION_MAGNITUDE_BUT_NO_PREREGISTERED_ANCHOR_HAS_STABLE_INCREMENTAL_DIRECTIONAL_SURVIVAL_EDGE`

## Current formal status

`BTC_AI_V1_OHLC_EVENT_ANCHORS_EXPLAIN_MAGNITUDE_NO_STABLE_DIRECTIONAL_SURVIVOR`

- formal supported candidates: **0**
- no event-anchor candidate PnL was opened
- 2026 was not opened
- no sparse or weak anchor was rescued

## Current next stage

`BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_CONDITIONAL_MODEL_PREREGISTRATION`

Latest handoff:

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_EVENT_ANCHOR_NO_SUPPORT_PATH_SHAPE_NEXT_20260803.md`

The next design must retain all anchor families and model the evolving post-anchor state. Magnitude and direction must be separate tasks. Direction must be evaluated as incremental residual versus matched baseline and must transfer across four half-years and D1 regimes before candidate PnL.

No external data, portfolio, Shadow, Discord, MT5 orders, live-ready or final signal is authorized.

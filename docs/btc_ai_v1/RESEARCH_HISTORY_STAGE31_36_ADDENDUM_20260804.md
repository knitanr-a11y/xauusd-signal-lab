# BTC AI V1 — Research History Addendum, Stages 31–36

Date: 2026-08-04

This addendum continues `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md` after Stage 30.

## Stage 31 — rolling adaptive recalibration

- monthly EXPANDING versus rolling 3/6/12-month training;
- 24 months × 4 schedules × 2 directions = 192 evaluations;
- resolved-only training and previous-month-only P90 calibration;
- leakage violations: 0;
- supported schedules: 0;
- formal result: `BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_NO_SUPPORTED_SCHEDULE`.

## Stage 32 — drift attribution and rank stability

- 144 validation-month rank comparisons;
- 144 previous-complete-month, past-only model-disagreement comparisons;
- hard rolling materially reduced training samples and changed ranking before validation outcomes were known;
- rolling-exclusive SHORT selections were consistently worse than expanding-exclusive selections;
- no past-only diagnostic consistently predicted next-month rolling benefit;
- supported live drift gates: 0.

Formal result:

`BTC_AI_V1_HARD_WINDOW_SAMPLE_LOSS_AND_PAST_VISIBLE_RANK_INSTABILITY_NO_SUPPORTED_LIVE_DRIFT_GATE`

## Stage 33 — soft recency weighting

- expanding training history retained; no historical row deletion;
- exponential half-lives: 3, 6, 12 and 24 months;
- 192/192 weighted evaluations available;
- leakage violations: 0;
- all SHORT half-lives had negative mean AUC delta versus unweighted expanding;
- supported half-lives: 0.

Formal result:

`BTC_AI_V1_OHLC_SOFT_RECENCY_WEIGHTING_NO_SUPPORTED_HALF_LIFE`

## Stage 34 — expanding/decay P90 consensus

- consensus required both EXPANDING and the same decay model to independently exceed their previous-month-calibrated P90 thresholds;
- 192 monthly schedule/direction evaluations;
- causal selection violations: 0;
- local precision gains failed density, monthly persistence, D1 transfer, half-year dependency, or the same-setting LONG/SHORT requirement;
- supported half-lives: 0.

Formal result:

`BTC_AI_V1_OHLC_EXPANDING_DECAY_CONSENSUS_NO_SUPPORTED_HALF_LIFE`

## Stage 35 — causal cooldown density

- chronological 1h, 4h and 12h cooldowns carried across month boundaries;
- labels were not used in cooldown selection;
- 576 monthly records;
- causal selection violations: 0;
- cooldown removed approximately 50–90% of consensus events and generally reduced label lift;
- supported configurations: 0.

Formal result:

`BTC_AI_V1_OHLC_CONSENSUS_CAUSAL_COOLDOWN_NO_SUPPORTED_CONFIGURATION`

## Stage 36 — OHLC-only adaptation search exhaustion synthesis

Formal status:

`BTC_AI_V1_OHLC_ONLY_ORDERING_AND_ADAPTATION_SEARCH_EXHAUSTED_THROUGH_STAGE35_NO_SUPPORTED_CANDIDATE`

- supported candidates: 0;
- candidate PnL: unopened;
- 2026: unopened;
- no further window, half-life, threshold, cooldown, direction, month, D1 or volatility rescue is authorized within the consumed OHLC information universe;
- a new research cycle requires explicit user authorization for a genuinely new causal information source or a new label/execution objective frozen before outcomes;
- Shadow, Discord, MT5 orders, live-ready and final signal remain OFF.

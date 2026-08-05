# BTC AI V1 — Stage 33 soft recency weighting result

Date: 2026-08-04

Formal status:

`BTC_AI_V1_OHLC_SOFT_RECENCY_WEIGHTING_NO_SUPPORTED_HALF_LIFE`

## Contract and causal execution

- expanding training history retained from 2023-01-01;
- no historical row deletion;
- exponential half-lives: 3, 6, 12 and 24 months;
- only labels with `maturity_ns <= current monthly refit_time` entered training;
- previous complete calendar month only for P90 calibration;
- evaluation: 2024-01 through 2025-12 exactly once;
- 24 months × 4 half-lives × 2 directions = 192 weighted evaluations;
- available evaluations: 192;
- leakage violations: 0;
- candidate PnL and 2026: unopened.

Execution used LightGBM `n_jobs=4` only as a computational setting. A complete 2024-01 rerun against `n_jobs=1` produced zero difference in AUC, Brier, calibration slope, score PSI, P90 threshold, P90 lift, score mean and score P90.

## Frozen gate results against unweighted expanding

| Half-life | Direction | Mean AUC delta | Positive AUC months | Mean P90-lift delta | Positive lift months | Median score PSI | Result |
|---|---|---:|---:|---:|---:|---:|---|
| EXP_DECAY_HL3M | LONG | +0.00043 | 14 | +0.03871 | 15 | 0.354 | FAIL |
| EXP_DECAY_HL3M | SHORT | -0.01280 | 8 | +0.00299 | 10 | 0.452 | FAIL |
| EXP_DECAY_HL6M | LONG | +0.00244 | 14 | -0.00647 | 11 | 0.186 | FAIL |
| EXP_DECAY_HL6M | SHORT | -0.00724 | 9 | +0.02055 | 11 | 0.223 | FAIL |
| EXP_DECAY_HL12M | LONG | +0.00210 | 15 | -0.01666 | 13 | 0.164 | FAIL |
| EXP_DECAY_HL12M | SHORT | -0.00472 | 5 | +0.01134 | 15 | 0.171 | FAIL |
| EXP_DECAY_HL24M | LONG | +0.00196 | 13 | -0.01549 | 12 | 0.155 | FAIL |
| EXP_DECAY_HL24M | SHORT | -0.00413 | 8 | -0.00774 | 10 | 0.163 | FAIL |

## Findings

- HL3M LONG improved mean P90 lift by +0.03871 and had 15 positive-lift months, but mean AUC improvement was only +0.00043, positive AUC months were 14, half-year concentration exceeded the frozen limit, and median score PSI was 0.354.
- HL6M LONG had mean AUC delta +0.00244 but mean P90-lift delta -0.00647 and negative D1-DOWN mean lift.
- HL12M LONG reached 15 positive AUC months but mean AUC delta was only +0.00210 and mean P90-lift delta was -0.01666.
- Every SHORT half-life had negative mean AUC delta: -0.01280, -0.00724, -0.00472 and -0.00413 for HL3/6/12/24M.
- No half-life passed every frozen gate for either direction, and no same half-life passed LONG and SHORT.

## Formal conclusion

Keeping the full expanding sample removes hard-window sample deletion, but fixed exponential recency weighting still does not create stable two-direction ordering improvement. Faster adaptation can help selected LONG months while damaging SHORT ordering and/or score stability.

No direction-specific rescue, half-life rescue, threshold change or gate reduction is authorized.

## Authorization

- supported half-lives: 0;
- supported candidates: 0;
- candidate PnL: unopened;
- 2026: unopened;
- Shadow, Discord, MT5 orders, live-ready and final signal: OFF.

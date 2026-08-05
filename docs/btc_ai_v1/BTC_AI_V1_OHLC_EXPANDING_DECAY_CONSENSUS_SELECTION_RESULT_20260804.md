# BTC AI V1 — Stage 34 expanding/decay consensus result

Date: 2026-08-04

Formal status:

`BTC_AI_V1_OHLC_EXPANDING_DECAY_CONSENSUS_NO_SUPPORTED_HALF_LIFE`

## Causal selection

For each half-life and direction:

`CONSENSUS = EXPANDING selected_p90 AND DECAY selected_p90`

Both component flags were independently calibrated using only the previous complete calendar month. No new threshold was created, and no current/future label entered selection.

- 24 months × 4 half-lives × 2 directions = 192 evaluations;
- causal audit violations: 0;
- 2026 and candidate PnL: unopened.

## Frozen gate results

| Half-life | Direction | Median monthly events | Months ≥20 | Mean consensus lift | Improvement vs EXPANDING | Positive improvement months | Result |
|---|---|---:|---:|---:|---:|---:|---|
| EXP_DECAY_HL12M | LONG | 159.0 | 21 | +0.0410 | -0.0123 | 11 | FAIL |
| EXP_DECAY_HL12M | SHORT | 100.5 | 23 | +0.0776 | +0.0136 | 12 | FAIL |
| EXP_DECAY_HL24M | LONG | 194.0 | 23 | +0.0616 | +0.0083 | 13 | FAIL |
| EXP_DECAY_HL24M | SHORT | 119.5 | 23 | +0.0601 | -0.0038 | 12 | FAIL |
| EXP_DECAY_HL3M | LONG | 23.0 | 15 | +0.1101 | +0.0683 | 16 | FAIL |
| EXP_DECAY_HL3M | SHORT | 24.0 | 14 | +0.0701 | -0.0031 | 8 | FAIL |
| EXP_DECAY_HL6M | LONG | 89.5 | 20 | +0.0760 | +0.0341 | 13 | FAIL |
| EXP_DECAY_HL6M | SHORT | 47.5 | 18 | +0.1056 | +0.0470 | 13 | FAIL |

## Findings

- HL3M LONG had mean lift improvement +0.0683 and 16 positive-improvement months, but only 15 months had at least 20 events and median monthly events were 23.
- HL6M LONG/SHORT had mean lift improvements +0.0341/+0.0470, but only 13 positive-improvement months each; SHORT also failed density and both failed the half-year dependency limit.
- HL12M and HL24M had adequate density but did not improve lift consistently; LONG also failed D1-DOWN transfer.
- No same half-life passed LONG and SHORT.

## Authorization

Supported consensus half-lives: 0. Candidate PnL, 2026, Shadow, Discord, MT5 orders, live-ready and final signal remain OFF.

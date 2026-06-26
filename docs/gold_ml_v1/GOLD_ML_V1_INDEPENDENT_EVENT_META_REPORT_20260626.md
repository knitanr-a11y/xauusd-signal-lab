# GOLD_ML_V1 independent-event meta-label search

Date: 2026-06-26

Status: `AUDIT_COMPLETE_ZERO_STRICT_CANDIDATES`

## Purpose

The frozen nine were treated as two parent LONG lineages, not nine independent strategies:

1. M15-H4 high-RCI / low-spread state.
2. H1-D1 BB60 upper breakout.

The search focused on different opportunities: SHORT pullbacks, upper/lower sweep failures, independent breakouts, squeeze releases and overextension reversals.

## Causal contract

- CSV `time` is MT5 server bar-open time.
- Decision time is bar-open plus timeframe duration.
- H1/H4/D1 features were joined only after their close.
- Entry used the exact M1 open at decision close.
- Same-M1 TP/SL collision used SL priority.
- Fold training used only outcomes resolved by the fold train-end timestamp.

## Independence pre-filter

The search excluded:

- all M15 decisions while the last closed H4 had RCI18 >= 73.993808 and spread/ATR <= 0.012772;
- all decisions within plus or minus 60 minutes of the existing H1 BB60-upper breakout parent event.

External overlap checks were all zero against those two existing parent definitions. Maximum pairwise Jaccard among the new frozen diagnostics was 5.46% in 2023 OOF and 6.35% externally.

## Search scale

- 12 event families.
- Three exit profiles: 1R/1R, 1R/1.5R and 1R/2R.
- 177 causal features.
- Logistic Regression, LightGBM, ExtraTrees and expected-R regression.
- Three purged chronological folds inside 2023.
- 1,954 single-score threshold rows.
- 12,554 two-model agreement-gate rows.

Strict 2023 OOF gate:

- at least 30 resolved;
- WR >= 60%;
- PF >= 2;
- at least five trades in every fold;
- at least two positive folds;
- minimum fold PF >= 0.8.

Strict pass count: **0**.

## Closest OOF diagnostic

`GML1-INDEP-DIAG-01` was a LONG reversal after downside overextension, outside both existing parent states.

- 2023 OOF: 51 resolved, WR 62.75%, PF 1.664, mean R 0.243.
- All three folds had positive mean R.
- It was not eligible because PF remained below 2.

Fixed external results:

| Year | Resolved | WR | PF | Total R |
|---:|---:|---:|---:|---:|
| 2024 | 113 | 46.90% | 0.879 | -6.953 |
| 2025 | 112 | 51.79% | 1.096 | 4.991 |
| 2026 diagnostic | 93 | 46.24% | 0.836 | -8.180 |

The 2023 interaction did not generalize.

## Frozen diagnostic shortlist

Six diverse diagnostics were frozen using 2023 only. SHA256:

`53bf242f0d58bf4879329ba9c4f3e0d2dcb4b3b23940bb1b109ab552fc6c2f7b`

None met WR >= 60% and PF >= 2 in both 2024 and 2025. No threshold, feature or model was changed after opening external periods.

## Decision

- Existing nine unchanged.
- Active new candidates: 0.
- No independent candidate promoted.
- Root BAT unchanged.
- Health gate OFF.
- Live-ready, final signal, MT5 and Discord OFF.

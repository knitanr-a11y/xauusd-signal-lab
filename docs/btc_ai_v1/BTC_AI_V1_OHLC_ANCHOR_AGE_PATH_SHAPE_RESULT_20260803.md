# BTC AI V1 — OHLC Anchor-Age Path-Shape Conditional Model Result

Date: 2026-08-03  
Status: `COMPLETE_NO_MAGNITUDE_OR_DIRECTION_SUPPORT_SURVIVOR`

## Authority

- accepted XM `BTCUSD#` closed-bar OHLC only
- MT5 broker-server naive time
- no external-market or volume features
- fixed spread remains 22.50 USD for any later candidate stage
- development evaluation: 2024-01 through 2025-12, exactly 24 calendar months
- 2026 remained unopened
- no exact-M1 candidate PnL was opened in this stage

## Purpose

The preceding event-anchor forensic showed that causal OHLC anchors explain future excursion magnitude more clearly than invariant direction. This stage tested whether the evolving state after the anchor adds stable information beyond the current OHLC state itself.

The model received all six frozen anchor families and fifteen subtypes, anchor direction, age 1–16, ATR displacement, achieved MFE/MAE, pullback, total variation, acceptance/rejection, and the frozen 100 causal current-OHLC features with closed H1/H4/D1 context.

Magnitude and direction were modeled separately. Direction was observed continuation/reversal value minus a cross-fitted ordinary-M15 baseline expectation.

## Data and support

- 2023 anchors were training-only and never counted as support;
- anchors generated in 2023–2025: 42,018;
- anchor-age rows generated: 672,257;
- formal development rows: 461,483 over 24 months;
- ordinary-M15 baseline rows: 112,784 directed rows;
- all six families and fifteen subtypes were retained.

## Implementation incidents and accepted rerun

1. Parquet support was unavailable. Serialization stopped before modeling and was replaced by pickle/numpy without changing rows or definitions.
2. The first preparation dry run allowed negative MFE/MAE. Those 672,257 rows were discarded before modeling and rebuilt with zero-origin excursion definitions.
3. The first LightGBM wrapper omitted `subsample_freq`; row bagging was therefore inactive. All initial 2024 metrics and partial 2025 models were invalidated. The accepted result reran all four folds with `bagging_fraction=0.8`, `bagging_freq=1`, and 350 total boosting rounds.
4. The first aggregator timed out writing a redundant 1.38-million-row compressed CSV. Model predictions were complete; compact aggregation used the original NPZ predictions and did not change outcomes.

## Magnitude result

| Target | Rows | Baseline Spearman | Combined Spearman | Delta | MAE reduction | Pass |
|---|---:|---:|---:|---:|---:|---|
| future MFE, four bars | 461,483 | 0.1478 | 0.1456 | -0.0022 | -1.54% | no |
| future MAE, four bars | 461,483 | 0.1531 | 0.1535 | +0.0004 | -1.09% | no |
| future range, four bars | 461,483 | 0.3336 | 0.3368 | +0.0032 | -2.18% | no |

Magnitude support survivors: **0**.

No magnitude target had nonnegative improvement in all four half-years. None reached the frozen +0.03 Spearman improvement and 3% error reduction gates. Current OHLC contained almost all available four-bar magnitude information; anchor age and path shape did not add stable incremental value.

## Fold metrics

| Fold | Target | Rows | Baseline rho | Combined rho | Delta rho | MAE reduction | Residual rho |
|---|---|---:|---:|---:|---:|---:|---:|
| 2024H1 | MFE | 111,261 | 0.1481 | 0.1440 | -0.0041 | -0.0145 | -0.0176 |
| 2024H1 | MAE | 111,261 | 0.1539 | 0.1491 | -0.0048 | -0.0131 | -0.0449 |
| 2024H1 | range | 111,261 | 0.3240 | 0.3283 | +0.0043 | -0.0216 | -0.0132 |
| 2024H1 | direction | 111,261 | 0.0331 | 0.0326 | -0.0005 | +0.0004 | +0.0490 |
| 2024H2 | MFE | 115,803 | 0.1426 | 0.1461 | +0.0034 | -0.0144 | -0.0092 |
| 2024H2 | MAE | 115,803 | 0.1398 | 0.1430 | +0.0032 | -0.0119 | -0.0289 |
| 2024H2 | range | 115,803 | 0.3189 | 0.3222 | +0.0033 | -0.0288 | -0.0102 |
| 2024H2 | direction | 115,803 | 0.0169 | 0.0200 | +0.0031 | +0.0009 | +0.0414 |
| 2025H1 | MFE | 115,859 | 0.1566 | 0.1512 | -0.0054 | -0.0101 | -0.0190 |
| 2025H1 | MAE | 115,859 | 0.1655 | 0.1671 | +0.0016 | -0.0099 | -0.0035 |
| 2025H1 | range | 115,859 | 0.3645 | 0.3641 | -0.0003 | -0.0178 | +0.0172 |
| 2025H1 | direction | 115,859 | 0.0230 | 0.0298 | +0.0067 | +0.0007 | +0.0639 |
| 2025H2 | MFE | 118,560 | 0.1459 | 0.1424 | -0.0035 | -0.0224 | +0.0018 |
| 2025H2 | MAE | 118,560 | 0.1559 | 0.1569 | +0.0010 | -0.0090 | +0.0111 |
| 2025H2 | range | 118,560 | 0.3339 | 0.3394 | +0.0054 | -0.0189 | +0.0614 |
| 2025H2 | direction | 118,560 | 0.0296 | 0.0282 | -0.0014 | +0.0006 | +0.0653 |

## Directional residual result

- cross-fitted residual Spearman: **0.0541**;
- P90 selected state rows: **43,056 / 24 months = 1,794.00 per month**;
- active months: 24/24;
- monthly min / median / max: 1,025 / 1,755.5 / 2,602;
- selected actual residual mean: **+0.0411**;
- frozen requirement: +0.0800;
- selected observed mean: -0.1479;
- ordinary baseline expectation: -0.1890.

These are overlapping anchor-state rows, not completed trades.

### Half-year

| Half-year | Rows | Actual residual mean | Observed | Baseline | Tail rho |
|---|---:|---:|---:|---:|---:|
| 2024H1 | 8,874 | +0.0540 | -0.1413 | -0.1953 | 0.1474 |
| 2024H2 | 11,318 | +0.0402 | -0.1448 | -0.1850 | 0.1311 |
| 2025H1 | 10,629 | +0.0552 | -0.1341 | -0.1892 | 0.1239 |
| 2025H2 | 12,235 | +0.0202 | -0.1677 | -0.1879 | 0.1223 |

All four signs were positive, but the effect weakened materially in 2025H2.

### D1

| D1 state | Rows | Actual residual mean | Tail rho |
|---|---:|---:|---:|
| DOWN | 12,023 | **-0.0042** | 0.1163 |
| NEUTRAL | 11,739 | +0.0465 | 0.1642 |
| UP | 19,294 | +0.0659 | 0.1003 |

The realized residual became negative in D1-DOWN, so the relation did not transfer across D1 states.

### Anchor family

| Family | Rows | Share | Actual residual mean | Tail rho |
|---|---:|---:|---:|---:|
| causal swing turn | 15,769 | 36.62% | +0.0531 | 0.1442 |
| compression expansion | 433 | 1.01% | +0.0832 | -0.0136 |
| EMA20 slope turn | 3,608 | 8.38% | +0.0180 | 0.1220 |
| failed range break | 7,702 | 17.89% | +0.0643 | 0.1581 |
| phase transition | 10,011 | 23.25% | +0.0240 | 0.0898 |
| range break | 5,533 | 12.85% | +0.0169 | 0.0694 |

Compression-expansion cannot be isolated: it had only 433 selected rows and negative within-family score correlation.

### Age finding

Actual residual was positive for most ages but became negative at ages 13 and 14. Selecting favorable ages now would be post-result filtering and is prohibited.

## Feature importance

Aggregate gain share:

- current OHLC: **79.26%**;
- post-anchor path core: **19.40%**;
- family identity: **0.71%**;
- subtype identity: **0.64%**.

The leading features were anchor direction, path displacement, path pullback, D1 EMA slope, achieved MFE, D1 slope acceleration, distance from D1 EMA50, and achieved MAE. Static family/subtype identity contributed only about 1.35%.

## Gate result

The overall residual correlation, time-sign, support, active-month and family-diversity gates passed. The load-bearing top-decile actual residual gate failed: +0.0411 versus required +0.0800. Realized D1-DOWN transfer also failed.

## Formal conclusion

`ANCHOR_AGE_PATH_SHAPE_ADDS_SMALL_UNSTABLE_DIRECTIONAL_RESIDUAL_AND_DOES_NOT_IMPROVE_MAGNITUDE_BASELINE`

- magnitude support survivors: **0**;
- direction support survivors: **0**;
- leave-one-D1-regime-out: not opened;
- leave-one-family-out: not opened;
- candidate PnL: not opened;
- 2026: not opened;
- supported candidates remain **0**.

## Good findings retained

1. Post-anchor displacement, pullback and achieved excursions contain small incremental direction information.
2. Residual ordering was positive in all four half-years.
3. Failed-break and swing-turn states contained better-than-baseline subsets without one family dominating.
4. The accepted rerun was chronological and evaluated residuals against an ordinary-state baseline.

## Failed findings

1. Anchor path did not improve future MFE, MAE or range prediction.
2. Directional improvement was about half the frozen support requirement.
3. D1-DOWN realized residual failed.
4. Family names added little after current OHLC and path geometry.
5. Another larger generic model grid is not justified.

## Next direction

Preregister a causal delayed-confirmation state machine for every family: accepted continuation, failed acceptance/reclaim, shallow pullback, deep pullback/exhaustion, stalled near-anchor, and mature extension. Define ATR/age bins before outcomes and require matched-baseline transfer across all half-years and D1 states before any candidate PnL.
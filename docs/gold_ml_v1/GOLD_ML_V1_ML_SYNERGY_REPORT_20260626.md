# GOLD_ML_V1 ML synergy audit — 2026-06-26

Status: `AUDIT_COMPLETE_ZERO_OOF_TARGET_CANDIDATES`

## What changed from the previous search

The previous broad search was mainly a rule grid plus explicit loss-zone removal. This audit instead treated the task as supervised time-series learning:

- Every valid closed M15 bar was scored separately for LONG and SHORT.
- Two fixed payoff profiles were used: 1R/1.5R and 1R/2R.
- 177 causal features from M15, H1, H4 and D1 were supplied simultaneously.
- A linear baseline, LightGBM classifier, ExtraTrees classifier and LightGBM expected-R regressor were trained.
- Fixed nonlinear blends combined win probability and expected R.
- Four expanding purged walk-forward folds were used inside 2023.
- Model score thresholds were selected using 2023 out-of-fold predictions only.
- 2024 validation, 2025 final test and 2026 diagnostics were opened only after the models and thresholds were frozen.

## Time and causality contract

- CSV `time` is MT5 server bar-open time.
- M15 decision time is `time + 15 minutes`.
- H1/H4/D1 bars were joined only when `bar_close_time <= decision_time`.
- Entry used the exact M1 open at the M15 close timestamp.
- Entry spread was known at that M1 open and normalized by decision ATR.
- Same-M1 TP/SL collision used SL priority.
- Open bars, future OHLC, future ATR and future higher-timeframe states were not used.

## Scale

| Item | Count |
|---|---:|
| Causal features | 177 |
| Independent direction/profile labels | 327,124 |
| 2023 OOF predictions | 61,988 |
| Score/threshold combinations evaluated | 660 |
| OOF candidates passing WR >= 60%, PF >= 2 and fold stability | **0** |
| Fixed external candidates passing the target in both 2024 and 2025 | **0** |

## OOF model quality

| profile | direction | model | mean AUC | minimum AUC | maximum AUC |
|---|---|---:|---:|---:|---:|
| P15 | LONG | ExtraTrees | 0.4931 | 0.4887 | 0.4956 |
| P15 | LONG | LightGBM | 0.4977 | 0.4812 | 0.5244 |
| P15 | LONG | Logistic | 0.4932 | 0.4743 | 0.5025 |
| P15 | SHORT | ExtraTrees | 0.5303 | 0.4871 | 0.5829 |
| P15 | SHORT | LightGBM | 0.5141 | 0.4644 | 0.5615 |
| P15 | SHORT | Logistic | 0.5223 | 0.4972 | 0.5679 |
| P20 | LONG | ExtraTrees | 0.4984 | 0.4863 | 0.5068 |
| P20 | LONG | LightGBM | 0.5012 | 0.4931 | 0.5108 |
| P20 | LONG | Logistic | 0.4968 | 0.4777 | 0.5095 |
| P20 | SHORT | ExtraTrees | 0.5248 | 0.4682 | 0.5877 |
| P20 | SHORT | LightGBM | 0.5209 | 0.4710 | 0.5893 |
| P20 | SHORT | Logistic | 0.5228 | 0.4833 | 0.5618 |

The nonlinear models learned feature interactions, but their chronological OOF AUC remained close to random. Interaction complexity did not create a stable predictive edge.

## Learned interaction structure

The following are actual parent-child split pairs from the fitted LightGBM trees, not manually invented filters:

| Feature A | Feature B | Tree edges | Total child gain |
|---|---|---:|---:|
| D1 range / ATR | H1 ADX14 | 52 | 1352.288 |
| D1 Bollinger width / ATR | M15 distance from prior 12-bar low | 32 | 736.697 |
| H1 realized volatility | H4 two-bar return / ATR | 27 | 1084.311 |
| D1 distance from prior 24-bar high | H1 realized volatility | 27 | 989.302 |
| D1 lower wick / ATR | H1 ADX14 | 27 | 774.223 |
| H1 ADX14 | H1 realized volatility | 26 | 656.981 |
| H1 ADX14 | H4 upper wick / ATR | 25 | 390.498 |
| D1 ADX14 | H4 wick balance | 24 | 908.593 |
| D1 distance from prior 48-bar low | H1 realized volatility | 24 | 876.034 |
| H4 ADX14 | H4 Bollinger width / ATR | 21 | 930.922 |

These interactions existed in the models, but they did not survive the chronological target gate.

## Best fixed external diagnostic — not a candidate

`P20-LONG-LOGIT-0.62500000` was the strongest fixed diagnostic across 2024 and 2025. It was selected only as a 2023 near-target diagnostic.

| Stage | 2024 | 2025 | 2026 diagnostic |
|---|---:|---:|---:|
| Raw score-selected rows | 698 | 622 | 3,581 |
| Dedup / one-open | 174 | 133 | 668 |
| Health gate | OFF: 174 | OFF: 133 | OFF: 668 |
| Resolved-only | 174 | 133 | 667 |
| Win rate | 39.7% | 39.1% | 32.1% |
| Profit factor | 1.223 | 1.213 | 0.922 |
| Mean R | 0.134 | 0.128 | -0.053 |
| Total R | 23.230 | 17.017 | -35.258 |
| Max DD R | 11.145 | 9.000 | 55.086 |

Although this diagnostic was positive in 2024 and 2025, its win rate was only about 39% and it degraded to PF below 1 in 2026. It does not meet the requested objective and is not activated.

### Monthly diagnostics

| Year | Months with trades | Negative months | Positive months | Zero months |
|---:|---:|---:|---:|---:|
| 2024 | 9 | 2 | 6 | 1 |
| 2025 | 9 | 4 | 5 | 0 |
| 2026 | 6 | 3 | 3 | 0 |

### Volatility diagnostics

| Year | Volatility | Resolved | Win rate | PF | Mean R | Total R |
|---:|---|---:|---:|---:|---:|---:|
| 2024 | Low | 74 | 40.5% | 1.255 | 0.151 | 11.206 |
| 2024 | High | 100 | 39.0% | 1.201 | 0.120 | 12.023 |
| 2025 | Low | 64 | 37.5% | 1.236 | 0.143 | 9.179 |
| 2025 | High | 69 | 40.6% | 1.191 | 0.114 | 7.838 |
| 2026 | Low | 266 | 32.0% | 0.918 | -0.055 | -14.763 |
| 2026 | High | 401 | 32.2% | 0.924 | -0.051 | -20.495 |

Both high- and low-volatility segments degraded in 2026, so a simple volatility gate would not solve the problem without external-period retuning.

## Interpretation

1. The previous failure was not caused only by insufficient interaction search. A true nonlinear ensemble also failed the 2023 chronological OOF target.
2. The models found many apparent interactions, but most were regime-specific and did not provide stable forward discrimination.
3. The best external result came from the linear model rather than the nonlinear blends. Adding interaction complexity increased fit complexity but not reliable edge.
4. Selecting or modifying a model after seeing the 2024–2026 results would be forbidden retuning.

## Decision

- Existing nine candidates remain unchanged.
- Active new candidate count remains zero.
- No ML model, threshold or interaction rule is promoted.
- Health gate remains OFF.
- `live_ready`, `final_signal`, MT5 orders, Discord and automatic promotion remain OFF.
- The correct next ML direction is event-specific meta-labeling or sequence learning under a newly predeclared 2023-only contract, not further tuning of these already-exposed models.

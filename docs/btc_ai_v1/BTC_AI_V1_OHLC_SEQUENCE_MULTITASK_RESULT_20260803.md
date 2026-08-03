# BTC AI V1 — OHLC Sequence Transition-Hazard Multi-task Result

Date: 2026-08-03  
Status: `COMPLETE_NO_PROVISIONAL_DEVELOPMENT_SURVIVOR`

## Authority and periods

- accepted XM `BTCUSD#` closed-bar OHLC only
- no external-market or volume features
- MT5 broker-server time
- closed M15 decision and exact next-M1 execution
- fixed spread: 22.50 USD per completed 1 BTC trade
- development: 2024-01 through 2025-12, exactly 24 calendar months
- consumed 2026-01 through 2026-07 period was not opened

## Method

Each decision used the previous 64 closed M15 bars, equal to 16 hours, plus the latest fully closed H1/H4/D1 OHLC context.

The models jointly addressed:

1. first named OHLC phase transition within the next 16 M15 bars;
2. LONG and SHORT MFE over the next 480 exact M1 bars;
3. LONG and SHORT MAE;
4. LONG and SHORT fixed-policy payoff using a 1 ATR stop, 2 ATR target and 480-minute maximum hold.

Compared models:

- `LGBM_SEQUENCE_BASELINE`: lagged values and 64-bar summary statistics;
- `GRU_MULTITASK`: a shared 32-unit GRU with hazard and path/payoff heads.

## Input and candidate counts

- valid continuous sequence/target rows: 100,948
- raw candidate definitions: 32
- outcome-blind capability survivors: 32
- candidate event frequency: 250–1,156 events over 24 months
- event frequency per month: 10.42–48.17
- exact-M1 execution configurations: 256

## Aggregate result

- positive-net configurations: 88 / 256
- PF >= 1.20 configurations: 0 / 256
- provisional development survivors: 0
- leave-one-D1-regime-out: not opened
- leave-one-transition-out: not opened
- bootstrap and matched-random: not opened
- 2026 diagnosis: not opened

## Strongest configurations

| Config | Model | Side / score | Completed trades / period | Trades/month | Monthly min/median/max | PF | Net | DD | Positive months | Positive half-years |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `SQ9_009__S1.0_T2.0_H480` | LightGBM baseline | SHORT payoff P95 cooldown | 580 / 24 months | 24.17 | 4 / 23.5 / 60 | 1.1539 | +21,262.16 | 8,877.90 | 13/24 | 3/4 |
| `SQ9_030__S1.0_T2.0_H720` | GRU multi-task | SHORT path-edge P97.5 first-cross | 363 / 24 | 15.13 | 4 / 15.5 / 30 | 1.1496 | +13,276.96 | 8,037.61 | 13/24 | 2/4 |
| `SQ9_006__S0.75_T2.0_H480` | LightGBM baseline | LONG path-edge P97.5 first-cross | 254 / 24 | 10.58 | 3 / 10.5 / 22 | 1.1485 | +4,648.74 | 3,866.08 | 11/24 | 3/4 |

None reached the frozen PF 1.20 minimum. The first and third also failed the 15-positive-month requirement. The GRU configuration additionally failed half-year persistence and the D1-regime PF floor.

## Model diagnostics

### Transition hazard

Validation balanced accuracy:

- LightGBM: 0.333–0.469
- GRU: 0.196–0.281

Validation macro-F1:

- LightGBM: 0.306–0.351
- GRU: 0.188–0.308

The non-neural lag/summary baseline classified phase transitions more reliably than the GRU.

### Path and payoff ordering

LightGBM validation Spearman:

- MFE/MAE heads: approximately 0.150–0.247
- direct fixed-policy payoff heads: approximately 0.000–0.055

GRU validation Spearman:

- path-edge scores: approximately 0.023–0.102
- direct fixed-policy payoff: approximately -0.006–0.038

OHLC sequences contained information about future excursion size, but both models had very weak ability to rank the discrete fixed-policy payoff directly.

## Why the best tail stopped near PF 1.15

### Best LightGBM SHORT

The P95 score selected better-than-unconditional fixed-policy payoff in every validation half-year.

| Fold | Selected payoff mean | All-row payoff mean | Selected positive rate | All-row positive rate |
|---|---:|---:|---:|---:|
| 2024H1 | -0.0367 | -0.1181 | 31.64% | 29.89% |
| 2024H2 | +0.0990 | -0.0826 | 36.59% | 31.03% |
| 2025H1 | +0.1190 | -0.0856 | 38.59% | 31.10% |
| 2025H2 | +0.0868 | -0.0504 | 37.01% | 31.97% |

The score therefore was not random. However, the improvement was thin: 2024H1 remained negative, 2025H1 exact-exit PF fell below one, and only 13 of 24 months were profitable.

Half-year exact-exit result:

- 2024H1: 108 trades, PF 1.0392, +836.12
- 2024H2: 159, PF 1.2024, +7,830.97
- 2025H1: 146, PF 0.9315, -2,850.01
- 2025H2: 167, PF 1.4233, +15,445.08

### Best GRU SHORT

The GRU selected a negative-payoff tail in both 2024 half-years and a positive tail in 2025.

Selected fixed-policy payoff mean:

- 2024H1: -0.1981
- 2024H2: -0.0562
- 2025H1: +0.1840
- 2025H2: +0.1534

Its exact-exit half-years were:

- 2024H1: 47 trades, PF 0.7164
- 2024H2: 80, PF 0.9823
- 2025H1: 149, PF 1.4573
- 2025H2: 87, PF 1.1249

D1-regime performance was also unstable:

- D1 DOWN: 68 trades, PF 1.4606
- D1 NEUTRAL: 134, PF 1.5100
- D1 UP: 161, PF 0.7575

The GRU learned a relation that became useful mainly in 2025 and outside D1-up conditions. It did not create the required time/regime invariance.

## Formal interpretation

`SEQUENCE_INFORMATION_EXISTS_BUT_GENERAL_SEQUENCE_MODELS_DID_NOT_CREATE_STABLE_PAYOFF_ORDERING_ACROSS_TIME_AND_D1_REGIMES`

The sequence experiment supports three conclusions:

1. OHLC paths contain measurable information about future MFE and MAE.
2. A general GRU did not outperform the simpler engineered lag/summary baseline.
3. The unresolved problem is not the absence of sequence information; it is that payoff meaning changes by event anchor, time and higher-timeframe state.

This agrees with the earlier phase/transition expert result: event-local conditioning improved PF more than one general sequence representation, but those local edges were sparse.

## Formal conclusion

- supported candidates: **0**
- no gate was relaxed
- no local winner or sequence near-candidate was rescued
- transfer, robustness and 2026 were not opened
- no Shadow, Discord, MT5 order, live-ready or final signal is authorized

## Next stage

`BTC_AI_V1_OHLC_EVENT_ANCHORED_TRAJECTORY_AND_SURVIVAL_FORENSIC_PREREGISTRATION`

Before another broad model search, the next work should align each sequence to a causal event anchor—such as a range break, swing extreme, expansion candle or phase-transition start—and study how continuation/reversal hazard changes with bars-since-anchor and ATR-distance-since-anchor. This must include all preregistered anchor families, not only previously profitable patterns.

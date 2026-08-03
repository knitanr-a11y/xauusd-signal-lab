# BTC AI V1 — OHLC State-Transition Representation Result

Date: 2026-08-03  
Status: `COMPLETE_NO_DEVELOPMENT_SURVIVOR`

## Scope

- authoritative source: accepted XM `BTCUSD#` closed-bar OHLC only
- no external data, volume feature or spread feature
- development: 2024-01 through 2025-12, exactly 24 calendar months
- 2026 remained unopened because no development survivor existed

## Research design

- 100 causal OHLC features, including impulse age/distance, maturity/exhaustion, acceptance/rejection and higher-timeframe phase
- six outcome-blind phases and six transition types
- LightGBM depth-3 and regularized logistic models
- state-only and base-OHLC-plus-state feature sets
- LONG and SHORT; P90/P95/P97.5; first-cross and four-bar cooldown
- 48 raw candidate definitions and eight fixed exact-M1 exit configurations

## Results

- raw candidates: 48
- outcome-blind capability survivors: 48
- exact-M1 execution configurations: 384
- positive-net configurations: 72
- configurations with PF >= 1.15: 0
- full development-gate survivors: 0

The highest PF was 1.1302, below the frozen 1.15 minimum. Therefore leave-one-phase-out, leave-one-transition-out, bootstrap, matched-random and 2026 diagnosis were not opened.

## Best configurations

| Candidate | Model | Features | Side | Threshold | Policy | Exit | Trades/24m | Trades/month | PF | Net | Positive months | Positive half-years |
|---|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| `ST6_010` | LGBM_D3 | OHLC_BASE_PLUS_STATE | SHORT | P97.5 | FIRST_CROSS | S1.0/T2.0/H720 | 290 | 12.08 | 1.1302 | +9,209.23 | 12/24 | 3/4 |
| `ST6_010` | LGBM_D3 | OHLC_BASE_PLUS_STATE | SHORT | P97.5 | FIRST_CROSS | S1.0/T2.0/H480 | 290 | 12.08 | 1.1227 | +8,672.54 | 13/24 | 2/4 |
| `ST6_010` | LGBM_D3 | OHLC_BASE_PLUS_STATE | SHORT | P97.5 | FIRST_CROSS | S1.0/T1.5/H720 | 299 | 12.46 | 1.1199 | +7,919.33 | 13/24 | 3/4 |
| `ST6_009` | LGBM_D3 | OHLC_BASE_PLUS_STATE | SHORT | P95 | COOLDOWN4 | S1.0/T2.0/H480 | 663 | 27.62 | 1.1037 | +16,103.07 | 14/24 | 4/4 |
| `ST6_032` | LOGIT_L2 | OHLC_BASE_PLUS_STATE | SHORT | P95 | FIRST_CROSS | S0.75/T1.5/H720 | 873 | 36.38 | 1.0782 | +12,775.20 | 15/24 | 3/4 |

## Best near-candidate phase decomposition

`ST6_010` used LightGBM with base OHLC plus state-transition features, SHORT P97.5 first-cross, 1 ATR stop, 2 ATR target and 720-minute hold. It completed 290 trades over 24 months (12.08/month), PF 1.1302, net +9,209.23, 12 positive months and three positive half-years.

Its phase performance was not concentrated in only one phase:

- MATURE_EXTENSION: 123 trades, PF 1.2649, net +7,172.53
- PULLBACK: 42 trades, PF 1.1387, net +1,393.28
- RANGE_NEUTRAL: 39 trades, PF 1.6079, net +5,249.20
- REVERSAL_ATTEMPT: 58 trades, PF 1.1571, net +2,314.81

This suggests the representation partially separated late extension from other states, but the total edge remained too thin and monthly consistency was insufficient. It is not a candidate and is not eligible for 2026 diagnosis.

## Gate failure counts

- completed_trades_ge_120: 384 / 384
- pf_ge_1_15: 0 / 384
- net_positive: 72 / 384
- positive_halfyears_ge_3: 44 / 384
- positive_months_ge_15: 8 / 384
- month_concentration_pass: 384 / 384
- phase_pf_floor_pass: 28 / 384
- phase_concentration_pass: 384 / 384

## Formal conclusion

`GLOBAL_OHLC_STATE_FEATURE_MODEL_DID_NOT_REACH_PREREGISTERED_EDGE`

The initial state-transition representation improved interpretability and produced several positive configurations, but it did not create a sufficiently strong and monthly persistent edge. The next distinct method must not loosen thresholds; it must prevent score comparability across phases by fitting and calibrating separate phase-conditional experts.

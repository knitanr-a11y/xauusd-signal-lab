# BTC AI V1 — Binance Futures External Validation Result

Date: 2026-08-03  
Status: `COMPLETE_NO_SUPPORTED_CANDIDATE_CONTINUE_TO_INDEPENDENT_SPOT_HISTORY`

## Source

- Binance official public archive
- `BTCUSDT` USD-M perpetual futures
- UTC, exact 1-minute bars
- 2020-01-01 through 2022-12-31
- 1,578,240 M1 rows, 100% calendar-minute coverage
- duplicate timestamps: 0
- non-ascending timestamps: 0
- missing minutes: 0
- 36 monthly funding-rate archives available and checksum-verified

GitHub Actions run: `30786496193`.

## Frozen period roles

- fit: 2020-01 through 2020-12, 12 months
- calibration: 2021-01 through 2021-06, 6 months
- development: 2021-07 through 2021-12, 6 months
- untouched final: 2022-01 through 2022-12, 12 months

Fixed execution:

- closed M15 decisions
- exact next M1 open
- fixed spread 22.50 USD per BTC
- 1 ATR stop
- 2 ATR target
- maximum hold 720 minutes
- same-M1 collision: SL first
- one-position non-overlap

## AI registry

48 frozen candidates from:

- LightGBM classifier
- XGBoost classifier
- ExtraTrees classifier
- Histogram Gradient Boosting classifier
- XGBoost fixed-policy payoff regressor
- ExtraTrees fixed-policy payoff regressor
- candle-context and microstructure/funding feature sets
- LONG and SHORT
- P90 and P95 calibration thresholds

Microstructure features included volume, quote volume, trade count, taker-buy share and funding.

## Development result — 6 calendar months

Four candidates passed all development gates.

| Candidate | Features | Side | Trades/6m | Trades/month | PF | Net | Positive months |
|---|---|---|---:|---:|---:|---:|---:|
| `BEX_MICRO_FUNDING_SHORT_XGB_P95` | micro + funding | SHORT | 94 | 15.67 | 1.3084 | +6,285.94 | 5/6 |
| `BEX_CANDLE_CONTEXT_SHORT_XGBR_P95` | candle | SHORT | 126 | 21.00 | 1.1948 | +4,962.12 | 4/6 |
| `BEX_MICRO_FUNDING_SHORT_EXTRA_P90` | micro + funding | SHORT | 122 | 20.33 | 1.1350 | +3,322.60 | 5/6 |
| `BEX_MICRO_FUNDING_LONG_HGB_P95` | micro + funding | LONG | 228 | 38.00 | 1.1240 | +5,452.62 | 4/6 |

## Robustness

Two candidates passed both frozen controls:

| Candidate | Bootstrap net-positive | Matched-random net percentile | Pass |
|---|---:|---:|---|
| `BEX_CANDLE_CONTEXT_SHORT_XGBR_P95` | 0.9240 | 0.9730 | yes |
| `BEX_MICRO_FUNDING_SHORT_XGB_P95` | 0.9410 | 0.9875 | yes |

The other two development candidates were rejected without rescue.

## Untouched 2022 result — 12 calendar months

| Candidate | Trades/12m | Trades/month | PF | Net | DD | Positive months | Final gate |
|---|---:|---:|---:|---:|---:|---:|---|
| `BEX_CANDLE_CONTEXT_SHORT_XGBR_P95` | 260 | 21.67 | 0.9850 | -536.84 | 6,176.72 | 4/12 | FAIL |
| `BEX_MICRO_FUNDING_SHORT_XGB_P95` | 94 | 7.83 | 1.1106 | +1,409.85 | 3,194.44 | 4/12 | FAIL |

The microstructure/funding XGBoost candidate remained slightly profitable but failed the preregistered requirement of at least seven positive months out of twelve. It is not promoted or rescued.

## Implementation incident

The first dry run compared M15 candidate row numbers with M1 resolution row numbers in the non-overlap gate, suppressing all trades after the first. That run was rejected. The accepted rerun compares exact M1 entry row with exact M1 resolution row. No first-run outcome was used.

## Formal conclusion

`NO_SUPPORTED_CANDIDATE_ON_BINANCE_FUTURES_2022_UNTOUCHED`

This result does not authorize Shadow, Discord, MT5 orders, portfolio construction, live-ready status or a final signal.

The next immediate track uses independently archived Binance spot history from 2018–2019 with the same frozen model registry and no use of 2019H2 outcomes for selection.

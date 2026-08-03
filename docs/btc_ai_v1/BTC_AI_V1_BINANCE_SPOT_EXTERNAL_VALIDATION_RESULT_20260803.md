# BTC AI V1 — Binance Spot External Validation Result

Date: 2026-08-03  
Status: `COMPLETE_NO_DEVELOPMENT_SURVIVOR_FINAL_REMAINS_UNOPENED`

## Source audit

Official Binance `BTCUSDT` spot monthly 1-minute archives were downloaded and verified against the published SHA256 checksums.

| Year | M1 rows | Calendar coverage | Gap intervals | Maximum gap | Duplicate/reversal | Price range |
|---|---:|---:|---:|---:|---:|---:|
| 2018 | 521,624 | 99.2435% | 9 | 2,010 minutes | 0 / 0 | 3,156.26–17,176.24 |
| 2019 | 523,836 | 99.6644% | 7 | 600 minutes | 0 / 0 | 3,349.92–13,970.00 |

- combined M1 rows: 1,045,460
- complete and exact usable M15 decision rows: 68,875
- interpolation: prohibited
- an M15 bar required all 15 constituent M1 rows
- entry-to-resolution required continuous exact M1 data through the 720-minute horizon
- any exchange outage or gap crossing was excluded and logged

Merged source hashes:

- 2018: `5628382b9756d8272566545af6876c8644b8c921306378110261129df71440f7`
- 2019: `0b451bf9488b4e770c9f13744eb689d4b2393b92e2c5e5b8fd6dd3a45c713dd9`

GitHub Actions run: `30787147478`.

## Frozen periods

- fit: 2018-01 through 2018-06, exactly 6 calendar months
- calibration: 2018-07 through 2018-12, exactly 6 months
- development: 2019-01 through 2019-06, exactly 6 months
- untouched final: 2019-07 through 2019-12, exactly 6 months

The final period was not opened because no candidate passed development.

## Fixed execution

- closed M15 decision
- exact next M1 open
- fixed spread: 22.50 USD per BTC
- 1 ATR stop / 2 ATR target
- 720-minute maximum hold
- SL first on a same-M1 collision
- one-position non-overlap

## AI registry

Forty-eight frozen candidate definitions:

- LightGBM classifier
- XGBoost classifier
- ExtraTrees classifier
- Histogram Gradient Boosting classifier
- XGBoost fixed-policy payoff regressor
- ExtraTrees fixed-policy payoff regressor
- candle-context and volume/trade-count/taker-buy feature sets
- LONG and SHORT
- P90 and P95 calibration thresholds

## Development result — 6 calendar months

- candidates evaluated: 48
- development survivors: 0
- robustness opened: no
- untouched 2019H2 opened: no

The highest development PF was only 0.7112 and remained negative.

| Rank | Candidate | Features | Side | Trades/6m | Trades/month | PF | Net | Positive months |
|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | `BSP_MICRO_VOLUME_LONG_EXTRA_P95` | volume/trades/taker | LONG | 397 | 66.17 | 0.7112 | -2,891.67 | 1/6 |
| 2 | `BSP_CANDLE_CONTEXT_LONG_EXTRA_P95` | candle | LONG | 276 | 46.00 | 0.6758 | -2,380.04 | 1/6 |
| 3 | `BSP_CANDLE_CONTEXT_LONG_XGB_P95` | candle | LONG | 290 | 48.33 | 0.6667 | -2,626.87 | 0/6 |
| 4 | `BSP_CANDLE_CONTEXT_LONG_EXTRAR_P95` | candle | LONG | 229 | 38.17 | 0.6462 | -2,438.81 | 0/6 |
| 5 | `BSP_MICRO_VOLUME_LONG_XGBR_P90` | volume/trades/taker | LONG | 439 | 73.17 | 0.5979 | -4,792.12 | 0/6 |

## Formal conclusion

`NO_DEVELOPMENT_VALUE_ON_BINANCE_SPOT_2019H1`

The failure occurred before robustness or untouched-final evaluation. No gate was relaxed and no candidate was rescued. The 2019H2 six-month period remains unopened but is not automatically transferable to an outcome-designed new candidate; a new research contract is required before it could be used.

No portfolio, Shadow, Discord, MT5 order, live-ready status or final signal is authorized.

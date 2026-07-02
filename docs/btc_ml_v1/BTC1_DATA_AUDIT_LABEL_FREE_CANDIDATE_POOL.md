# BTC-1 data audit and label-free candidate pool

## Status

`BTC1_DATA_AUDIT_AND_LABEL_FREE_CANDIDATE_POOL`

BTC remains audit-only:

- `orders_enabled = false`
- `discord_enabled = false`
- `live_ready = false`
- `final_signal = false`
- outcome evaluation has not started

The candidate conditions in `configs/btc_ml_v1/btc1_candidate_pool_contract.json` are frozen before TP/SL or return labels are calculated.

## Uploaded data audit

The inspected package was generated on 2026-07-02 UTC for the exact broker symbol `BTCUSD#`.

| Timeframe | Rows | Duplicates | Bad OHLC | Gaps |
|---|---:|---:|---:|---:|
| M1 | 129,209 | 0 | 0 | 13 |
| M5 | 209,588 | 0 | 0 | 108 |
| M15 | 69,969 | 0 | 0 | 106 |
| H1 | 17,519 | 0 | 0 | 0 |
| H4 | 4,379 | 0 | 0 | 0 |
| D1 | 729 | 0 | 0 | 0 |

All six CSV SHA-256 values matched the package manifest. All timestamps were strictly increasing and aligned to their timeframe. There were no non-finite OHLC values, negative spreads, negative tick volumes or zero tick-volume rows.

The lower-timeframe gaps were classified as scheduled Saturday maintenance or DST clock-transition gaps. No unexplained gap class was found.

## Cross-timeframe parity

Only complete child-bar groups were compared.

| Aggregation | Exact matches | Complete groups | Match rate |
|---|---:|---:|---:|
| M1 → M5 | 25,841 | 25,841 | 100% |
| M5 → M15 | 69,757 | 69,757 | 100% |
| M15 → H1 | 17,413 | 17,413 | 100% |
| H1 → H4 | 4,379 | 4,379 | 100% |
| H1 → D1 | 729 | 729 | 100% |

## Entry-time information contract

A BTC candidate is evaluated only after its M15 bar closes. Higher-timeframe values use the last H1/H4 bar whose close time is not later than that M15 decision time.

No candidate condition uses:

- a future high, low, close or volume;
- an open candle;
- TP/SL outcome;
- unresolved horizon result;
- a later rolling win rate;
- GOLD thresholds, directions or candidate IDs.

A future-data perturbation test changed every OHLC value after 2026-01-01. All 3,044 candidate events before that timestamp remained identical, confirming the implemented candidate calculation did not look forward.

## Frozen candidate families

Four structurally different and direction-symmetric families are retained. No family is removed based on results.

### TREND_PULLBACK

Aligned H1, H4 and M15 trend with an M15 pullback/rejection near EMA20 and a bounded RSI zone.

Observed label-free density:

- LONG: 1,362
- SHORT: 1,190
- total: 2,552
- median monthly events: 108

### BREAKOUT_EXPANSION

H1/H4 trend-aligned close through the prior 96 M15-bar extreme with body size at least 0.55 ATR14.

- LONG: 362
- SHORT: 339
- total: 701
- median monthly events: 28

### COMPRESSION_RELEASE

Prior Bollinger-width compression relative to its trailing 672-bar EMA, followed by expansion and a prior 20-bar extreme break.

- LONG: 397
- SHORT: 336
- total: 733
- median monthly events: 30

### RANGE_REVERSION

Flat H1 EMA20/EMA50 separation relative to H1 ATR, plus an M15 z-score/RSI extreme and reversal candle.

- LONG: 33
- SHORT: 53
- total: 86
- median monthly events: 3

This family is sparse but remains in the pool because outcomes have not been used to justify removing it.

## Overlap policy

BREAKOUT_EXPANSION and COMPRESSION_RELEASE overlap on 151 M15 bars. The family tags remain separate at this stage. Deduplication priority must not be chosen from outcome performance.

## M1 and M5 roles

- M5 covers the two-year research period and will be the primary TP/SL first-touch timeframe.
- M1 covers the recent 90-day audit period and will quantify same-M5-bar ambiguity, execution timing and spread behavior.
- For older M5 bars where TP and SL are both touched in one bar, the next stage must predeclare a conservative rule before measuring results. M1 cannot be fabricated for the older period.

## Next stage boundary

The next stage may attach predeclared M5 first-touch outcomes and use recent M1 only as an ambiguity audit. It must preserve the frozen candidate definitions and keep a final evaluation period untouched while target R, stop model and horizon variants are compared.

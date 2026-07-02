# BTC-2 candidate and exit exploration

## Status

`BTC2_CANDIDATE_EXIT_EXPLORATION_RESEARCH_ONLY`

BTC remains non-live:

- `orders_enabled = false`
- `discord_enabled = false`
- `live_ready = false`
- `final_signal = false`

The final holdout beginning 2026-01-01 remains untouched. No outcome after that date was calculated.

## Price, pip and time contracts

- User contract: `$10` price movement equals `1 pip`.
- Minimum take-profit: `50 pips`, equivalent to `$500` price movement.
- All fixed shortlisted targets are 100 or 125 pips. The ATR candidate has a 50-pip floor.
- CSV `time` is the candle open timestamp.
- An M15 candidate is decided at `source_bar_open + 15 minutes`.
- Entry is the exact M5 open whose timestamp equals the decision timestamp.
- Two BTC-1 events had no exact M5 open because of scheduled maintenance and were excluded.
- A bar is considered available only after its close time.

## Spread handling

The primary exploration assumes a `$30` spread, with `$20`, `$25` and `$30` sensitivity checks.

The package confirms:

- recent M1 spread: `$22.50`;
- M5 spread: `$30` through most of 2025, changing to `$22.50` from late 2025;
- older broker history included `$45` to `$74.66` spreads.

Targets are net of spread. For example, a 100-pip LONG target requires the bid to move `$1,000 + spread` above the entry bid.

## Evaluation isolation

- Discovery entries: 2024-07-03 through 2025-06-30.
- Validation entries: 2025-07-01 through 2025-12-31.
- A candidate is excluded from a period if its full maximum holding deadline would cross that period boundary.
- Final holdout entries from 2026-01-01 onward are stored with entry-known fields only.
- If TP and SL are both inside one M5 bar, the result is conservatively assigned to SL first.

## Primary candidates

### BTC2_CR_SHORT_LOW_VOL

Compression-release SHORT while:

```text
atr_fraction < 0.80 * EMA672(atr_fraction)
```

Exit:

```text
TP = 125 pips ($1,250 net)
SL = 37.5 pips ($375 net)
horizon = 48 hours
```

| Period | Trades | Average | PF | Win rate | Positive months | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Discovery | 62 | 17.54 pips | 1.707 | 33.9% | 81.8% | 337.5 pips |
| Validation | 32 | 18.36 pips | 1.746 | 34.4% | 83.3% | 300.0 pips |

The low win rate is intentional: target distance is 3.33 times the stop distance.

### BTC2_TP_LONG_HIGH_VOL

Trend-pullback LONG while:

```text
atr_fraction > 1.25 * EMA672(atr_fraction)
```

Exit:

```text
TP = 100 pips ($1,000 net)
SL = 75 pips ($750 net)
horizon = 48 hours
```

| Period | Trades | Average | PF | Win rate | Positive months | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Discovery | 122 | 13.93 pips | 1.378 | 50.8% | 66.7% | 1,325 pips |
| Validation | 60 | 21.25 pips | 1.630 | 55.0% | 80.0% | 500 pips |

## Secondary candidates

### BTC2_CR_SHORT_UTC16_23

Compression-release SHORT, decision time 16:00-23:59 UTC.

```text
TP 125 pips / SL 37.5 pips / horizon 48 hours
```

Discovery PF 2.020 and validation PF 2.048. Validation had only 50% positive months, so this remains secondary rather than replacing the low-volatility version.

### BTC2_TP_LONG_RSI54

Trend-pullback LONG with `RSI14 >= 54.22047006970092`. The threshold is the discovery-period median and was frozen before validation.

```text
TP 100 pips / SL 100 pips / horizon 36 hours
```

Discovery: 408 trades, PF 1.266. Validation: 173 trades, PF 1.476. It has more signals but larger drawdown than the high-volatility version.

### BTC2_BO_LONG_WEEKDAY_HIGH_VOL

Weekday breakout-expansion LONG while the high-volatility flag is true.

```text
TP 125 pips / SL 75 pips / horizon 24 hours
```

Discovery: 53 trades, PF 1.826. Validation: 30 trades, PF 1.275. The edge weakened in validation, so it remains secondary.

## Sparse watch candidate

### BTC2_RR_SHORT_ATR

Range-reversion SHORT:

```text
SL = max($250, 2.5 * entry ATR14)
TP = max($500, 1.5 * SL)
horizon = 36 hours
```

Discovery had 28 trades and validation 14 trades. It remains in research but cannot be promoted with this sample size.

## Candidates not promoted

- Trend-pullback SHORT failed to remain profitable in both discovery and validation.
- Range-reversion LONG failed validation.
- Compression-release LONG and unfiltered breakout variants had only marginal PF near 1 and were not promoted.

These families are not deleted from the BTC-1 candidate pool. The outcome results only define the BTC-2 shortlist.

## Next boundary

Before any final selection:

1. Keep all BTC-2 conditions unchanged.
2. Evaluate the untouched 2026 holdout once.
3. Use available M1 from April 2026 onward to audit M5 same-bar ordering and actual spread behavior.
4. Do not enable signals, Discord or orders without a separate explicit authorization.

# MOCHIPOYO_LIVE_NOTIFICATION_PLAN

## Status

This document defines the first live-notification plan for the Mochipoyo-style candidates.

AI review is intentionally disabled for the first live phase.

The first live phase should only send Discord notifications and record ledgers. It should not place trades automatically.

## Notification candidates

### GOLD

Use the baseline fixed-preset candidate:

```text
GOLD_MOCHIPOYO_RR12_REFINED
```

Reference fixed-preset performance:

```text
trades: 205
wins: 107
losses: 75
timeouts: 23
win_rate_resolved: 58.79%
total_r: +53.4R
PF: 1.712
max_dd_r: 4.8R
max_consecutive_losses: 4
```

Price-width summary:

```text
total_dollars: +1305.93 dollars
total_pips: +13059.28 pips
conversion: 1 dollar = 10 pips
```

GOLD final fixed-preset CSV:

```text
data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_final_portfolio.csv
```

GOLD fixed preset:

```text
config/mochipoyo/gold_mochipoyo_rr12_refined_fixed_filters.json
```

### BTC

Use the baseline fixed-preset candidate:

```text
BTC_MOCHIPOYO_H4_M15_A_NET_REFINED
```

Reference fixed-preset performance:

```text
trades: 123
wins: 59
losses: 36
timeouts: 28
win_rate: 62.11%
net_total_r: +26.38R
net_pf: 1.733
net_max_dd_r: 4.0R
max_consecutive_losses: 4
avg_spread_to_sl_ratio: 0.0539
avg_effective_rr_after_spread: 1.0948
```

Price-width summary:

```text
total_dollars: +16445.54 dollars
total_pips: +1644.55 pips
conversion: 10 dollars = 1 pip
```

BTC final fixed-preset CSV:

```text
data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset_final_portfolio.csv
```

BTC fixed preset:

```text
config/mochipoyo/btc_mochipoyo_h4_m15_a_net_refined_fixed_filters.json
```

## Why baseline, not only high-quality variants

The baseline candidates should be used for notification because live notification is for human confirmation, not auto-entry.

The high-quality variants are useful as labels, but they remove many otherwise valid review opportunities.

### GOLD variants

```text
GOLD baseline:
205 trades / PF1.71 / DD4.8R

GOLD no_granville_2_like:
104 trades / PF2.04 / DD6.8R
```

GOLD no_granville_2_like improves PF but cuts trade count roughly in half and increases DD in the reviewed window. Therefore, use baseline for notification and add caution labels to weaker shapes.

### BTC variants

```text
BTC baseline:
123 trades / net PF1.73 / DD4.0R / max loss streak 4

BTC no_buy_2_like:
83 trades / net PF1.97 / DD3.0R / max loss streak 3
```

BTC no_buy_2_like improves quality, but baseline still has acceptable spread-aware net results and more useful review signals. Therefore, use baseline for notification and add caution labels to Granville 2-like shapes.

## Mandatory live rules

### Common

```text
confirmed-time join only
context_close_time <= base_close_time
pivot_confirmed_time <= signal_close_time
entry_time >= signal_close_time
same-bar TP/SL ambiguity uses SL priority in backtest evidence
AI review disabled in first phase
no automatic order placement
Discord notification only
ledger every generated payload
```

### BTC-specific

```text
BTC notifications must come only from spread-aware net-positive candidates
BTC gross-only results are not adoption evidence
BTC spread must be read from CSV spread column or explicitly logged override
BTC candidate name and notification must show net-aware status
```

## Granville 2 caution policy

Granville 2-like signals are not excluded from baseline notifications.

They should be notified with explicit caution labels because manual review showed that many losses came from early entries around Granville 2-like pullbacks.

### Common labels

```text
[QUALITY: STANDARD]
[QUALITY: HIGH]
[CAUTION: GRANVILLE_2_LIKE]
[CAUTION: BUY_2_EARLY_ENTRY]
[CAUTION: SELL_2_EARLY_ENTRY]
[CAUTION: SPREAD_TO_SL_HIGH]
```

### Granville 3

Granville 3 is treated as the cleaner continuation/pullback completion shape.

Suggested message:

```text
Granville 3: pullback/retrace completion is more mature. Confirm lower-timeframe continuation before entry.
```

### Granville 2

Granville 2 is treated as earlier and more fragile.

Suggested message:

```text
Granville 2-like: setup may be early. Confirm lower-timeframe reversal/continuation before entry.
```

### BTC BUY_2

BTC BUY_2 receives stronger caution because review showed many BTC weak-month losses, especially April, came from BUY_2-like entries.

Suggested message:

```text
BTC BUY_2 caution: pushback/pullback buy may be early. Check whether M15 has actually turned and whether spread-to-SL is acceptable.
```

### BTC SELL_2

Suggested message:

```text
BTC SELL_2 caution: return-sell may be early. Check upper wick/rejection, RCI turn, and M15 breakdown before entry.
```

## Notification quality classes

### GOLD

```text
QUALITY HIGH:
- no_granville_2_like equivalent
- or Granville 3-only

QUALITY STANDARD:
- baseline fixed preset match

CAUTION:
- granville_buy_2_like
- granville_sell_2_like
- direction and lower timeframe EMA order look early/opposed
```

### BTC

```text
QUALITY HIGH:
- no_buy_2_like equivalent
- or no_granville_2_like equivalent
- or Granville 3-only

QUALITY STANDARD:
- baseline fixed preset match

CAUTION:
- granville_buy_2_like, especially BUY signals
- spread_to_sl_ratio > 0.07
```

## Discord notification content

Each notification should include:

```text
symbol
candidate name
timeframe pair
direction
entry timing basis
entry price candidate
SL price
TP price
RR
expected first-touch horizon
quality labels
caution labels
Granville type
EMA order
RCI state/turn
MACD divergence/hidden divergence reason
score fields
source fixed filter name/rank
spread fields for BTC
ledger id/path
```

BTC-specific fields:

```text
mode_spread_points
mode_spread_price
spread_to_sl_ratio
effective_rr_after_spread
net-aware label
```

## Example message skeleton

```text
[GOLD MOCHIPOYO SIGNAL]
Candidate: GOLD_MOCHIPOYO_RR12_REFINED
Quality: STANDARD
Caution: GRANVILLE_2_LIKE / BUY_2_EARLY_ENTRY if applicable
Pair: GOLD_H4_M15_DAYTRADE
Direction: BUY
Entry basis: confirmed M15 close, next bar open candidate
Entry: xxxx.xx
SL: xxxx.xx
TP: xxxx.xx
RR: 1.2
Granville: BUY_2 / BUY_3
Reason: ...
Scores: total/context/base = ...
Source filter: rank=..., name=...
Ledger: ...
```

```text
[BTC MOCHIPOYO SIGNAL]
Candidate: BTC_MOCHIPOYO_H4_M15_A_NET_REFINED
Quality: STANDARD
Caution: GRANVILLE_2_LIKE / BUY_2_EARLY_ENTRY / SPREAD_TO_SL_HIGH if applicable
Pair: BTC_H4_M15_DAYTRADE
Direction: BUY
Entry basis: confirmed M15 close, next bar open candidate
Entry: xxxxx.xx
SL: xxxxx.xx
TP: xxxxx.xx
RR: 1.2
Spread: mode_points=..., price=...
Spread/SL: ...
Effective RR after spread: ...
Granville: BUY_2 / BUY_3
Reason: ...
Scores: total/context/base = ...
Source filter: rank=..., name=...
Ledger: ...
```

## First live phase acceptance criteria

Before using notifications as trading support, collect live ledger rows first.

Minimum first review target:

```text
GOLD: at least 30 live signals or 1 month
BTC: at least 20 live signals or 1 month
```

During live review, compare:

```text
signal count
actual spread at notification time
whether entry was realistically available
whether SL/TP levels were sensible
whether Granville 2 caution labels helped avoid bad entries
whether BTC spread_to_sl_ratio is stable
post-signal first-touch outcome
```

## Next implementation steps

1. Implement live scanner from latest MT5 CSVs using fixed presets.
2. Generate payload rows but do not send first; run dry-run ledger.
3. Verify one or more historical recent signals reproduce known fixed-preset matches.
4. Add Discord notification formatting.
5. Start with dry-run or private Discord channel.
6. Keep AI review disabled until live ledger quality is confirmed.

## Decision

```text
GOLD notification candidate:
GOLD_MOCHIPOYO_RR12_REFINED baseline

BTC notification candidate:
BTC_MOCHIPOYO_H4_M15_A_NET_REFINED baseline

Granville 2-like:
do not exclude; notify with caution labels

AI review:
disabled for first live phase
```

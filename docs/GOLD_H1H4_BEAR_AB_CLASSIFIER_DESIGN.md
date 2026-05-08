# GOLD H1/H4 Bearish M15 Low-Break A/B Classifier

## Purpose

This document freezes the implementation plan for the bearish GOLD/XAUUSD candidate researched from the 2026-04-28 MT5-time H1 decline.

The candidate is intentionally separated from:

- Mochipoyo live/demo/autotrade flow
- GOLD C_ENV RR2 72h BUY candidate
- Any Discord real-send flow
- Any real MT5 order placement

The first implementation step is research/backtest reproduction and dry-run live scan only.

## Strategy family

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

SELL only.

The design uses two improved bearish sub-conditions:

1. A improved: stricter H1/H4 bearish environment + M15 low-break16 quality filter
2. B improved: broader bearish trend + M15 low-break6 momentum filter

The final output is not A and B as separate trades. It is a single ranked classifier:

```text
CORE_AB_CONFIRM = A and B
B_ONLY_SAFE     = B and not A
A_ONLY_OBSERVE  = A and not B
```

## Final signal IDs

### CORE

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_CORE_AB_CONFIRM_FIXED10_RR2_12H
```

Meaning:

```text
A improved condition passes
AND
B improved condition passes
```

Trade handling:

```text
trade_enabled = true
lot_multiplier = 2.0
rank = CORE_AB_CONFIRM
```

### B only

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_B_ONLY_SAFE_FIXED10_RR2_12H
```

Meaning:

```text
B improved condition passes
AND
A improved condition does not pass
```

Trade handling:

```text
trade_enabled = true
lot_multiplier = 1.0
rank = B_ONLY_SAFE
```

### A only

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_A_ONLY_OBSERVE_FIXED10_RR2_12H
```

Meaning:

```text
A improved condition passes
AND
B improved condition does not pass
```

Trade handling:

```text
trade_enabled = false
lot_multiplier = 0.0
rank = A_ONLY_OBSERVE
```

A-only is logged/observable research output, not an order-intent candidate.

## Indicator settings

All MACD values use:

```text
Fast EMA = 6
Slow EMA = 13
Signal EMA = 4
```

EMA/ATR:

```text
EMA20
EMA50
ATR14 = simple rolling mean of true range, 14 bars
```

Confirmed-time join rule:

```text
context_close_time <= m15_signal_close_time
```

This is enforced using backward asof joins from M15 close_time to H1/H4/D1 close_time.

## A improved condition

```text
H1:
  close < EMA20
  EMA20 < EMA50
  EMA20 slope3 < 0
  H1_DIST_E20_ATR <= 1.60

H4:
  close < EMA20
  EMA20 < EMA50

D1:
  close < EMA20

M15:
  low < previous rolling low 16
  close_pos <= 0.45
  MACD hist delta < 0
  range / ATR14 >= 0.90
```

Where:

```text
H1_DIST_E20_ATR = (H1 EMA20 - H1 close) / H1 ATR14
close_pos = (M15 close - M15 low) / (M15 high - M15 low)
range / ATR14 = (M15 high - M15 low) / M15 ATR14
```

The H1 distance filter is intended to avoid selling after H1 is already too extended below EMA20.

## B improved condition

```text
H1:
  close < EMA50
  EMA20 < EMA50
  H1_DIST_E20_ATR <= 1.60

H4:
  EMA20 < EMA50

D1:
  close < EMA20

M15:
  low < previous rolling low 6
  close_pos <= 0.50
  MACD hist < 0
  MACD hist delta < 0
```

## Ranking logic

Implementation must first compute booleans:

```text
a_pass
b_pass
```

Then normalize to one final signal per M15 bar:

```text
if a_pass and b_pass:
    rank = CORE_AB_CONFIRM
    condition_id = GOLD_H1H4_BEAR_M15_LOW_BREAK_CORE_AB_CONFIRM_FIXED10_RR2_12H
    trade_enabled = true
    lot_multiplier = 2.0

elif b_pass:
    rank = B_ONLY_SAFE
    condition_id = GOLD_H1H4_BEAR_M15_LOW_BREAK_B_ONLY_SAFE_FIXED10_RR2_12H
    trade_enabled = true
    lot_multiplier = 1.0

elif a_pass:
    rank = A_ONLY_OBSERVE
    condition_id = GOLD_H1H4_BEAR_M15_LOW_BREAK_A_ONLY_OBSERVE_FIXED10_RR2_12H
    trade_enabled = false
    lot_multiplier = 0.0

else:
    no signal
```

A and B must not be emitted as two independent trades on the same bar.

## Entry / SL / TP / exit

Backtest entry:

```text
signal_time = M15 bar open time
m15_close_time = signal_time + 15 minutes
entry_time = m15_close_time
entry_price = next M15 open
```

Live dry-run entry reference:

```text
entry_time = latest confirmed M15 close_time
entry_price_reference = next M15 open if already present, otherwise latest confirmed M15 close
```

SELL risk:

```text
SL = entry + 10.0
TP = entry - 20.0
RR = 2.0
max_hold = 12h
```

Outcome evaluation:

```text
M1 first-touch
same M1 bar TP/SL conflict = SL priority
if neither TP nor SL is hit within 12h, TIMEOUT at last checked M1 close
```

Rows that do not have a full 12h M1 horizon should not be treated as fully validated research outcomes.

## Cooldown

Initial implementation uses common cooldown across trade-enabled SELL ranks:

```text
cooldown_bars_m15 = 8
cooldown_minutes = 120
```

This means:

```text
CORE after B_ONLY is blocked inside cooldown
B_ONLY after CORE is blocked inside cooldown
A_ONLY is observe-only and is not part of traded cooldown output
```

The first pass deliberately avoids a CORE exception because that can overtrade the same impulse.

## Lot handling

Each payload should carry:

```text
base_lot
lot_multiplier
effective_lot
```

Formula:

```text
effective_lot = min(base_lot * lot_multiplier, max_lot_per_trade)
```

Defaults:

```text
base_lot = 0.10
CORE lot_multiplier = 2.0
B_ONLY lot_multiplier = 1.0
A_ONLY lot_multiplier = 0.0
```

The live/dry-run ledger must record both raw rank and effective lot so later review can compare:

```text
CORE only
B_ONLY only
CORE x2 lot-weighted
combined unweighted
combined lot-weighted
```

## Files

### Research/backtest

```text
scripts/research_gold_h1h4_bear_m15_low_break_ab_classifier.py
```

### Live dry-run scan once

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
```

## Research command

```cmd
python scripts\research_gold_h1h4_bear_m15_low_break_ab_classifier.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_m15_low_break_ab_classifier
```

## Live dry-run scan command

```cmd
python scripts\run_gold_h1h4_bear_ab_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan
```

If the MT5 CSV contains the currently forming M15 candle as the last row:

```cmd
python scripts\run_gold_h1h4_bear_ab_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan --latest-confirmed-policy second_last
```

## First validation from uploaded CSVs

Using the uploaded CSV set in the chat and the common cooldown implementation:

```text
cooldown trades: 68
CORE_AB_CONFIRM: 22 trades, WR 59.09%, total +17R, lot-weighted +34R, PF 2.89
B_ONLY_SAFE: 46 trades, WR 54.35%, total +29R, lot-weighted +29R, PF 2.38
combined unweighted: 68 trades, WR 55.88%, total +46R, PF 2.53, max DD 5R
combined lot-weighted: +63R, PF 2.62, max DD 6R
```

Target window 2026-04-28 07:00-14:00 MT5 time:

```text
CORE_AB_CONFIRM
entry_time = 2026-04-28 08:15:00
entry = 4652.40
SL = 4662.40
TP = 4632.40
outcome = WIN
realized = +2R
lot_multiplier = 2.0
lot-weighted = +4R
```

Note: these results use the unified classifier with common cooldown. They are not expected to be identical to earlier exploratory overlap statistics where A and B were compared as separate candidate lists.

## Next steps

1. Run the research script on the current MT5 CSV directory.
2. Confirm `summary_by_rank.csv`, `summary_overall_lot_weighted.csv`, `monthly_by_rank.csv`, and `target_window_20260428.csv`.
3. Run the live dry-run scan once.
4. Inspect `latest_scan_result.json`.
5. Only after dry-run lifecycle review, consider adding this family to a notification loop.
6. Do not connect to demo autotrade until dry-run ledger, duplicate control, lot multiplier, and position monitor behavior are reviewed.

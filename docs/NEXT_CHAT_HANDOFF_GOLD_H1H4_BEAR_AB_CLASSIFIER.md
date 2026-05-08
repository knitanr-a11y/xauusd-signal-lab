# NEXT CHAT HANDOFF - GOLD H1/H4 Bearish A/B Classifier

Use this as the first document to read in the next chat.

## Repository

```text
knitanr-a11y/xauusd-signal-lab
```

## Read these first

```text
docs/GOLD_H1H4_BEAR_AB_CLASSIFIER_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_H1H4_BEAR_AB_CLASSIFIER.md
```

## Objective

Continue the GOLD/XAUUSD bearish SELL candidate researched from the 2026-04-28 MT5-time H1 decline.

The implemented family is:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

It is separated from:

- Mochipoyo live/demo/autotrade flow
- GOLD C_ENV RR2 72h BUY candidate
- Discord real-send
- real MT5 order placement

## Core design

Compute two booleans on each confirmed M15 bar:

```text
a_pass
b_pass
```

Then normalize to one ranked signal:

```text
CORE_AB_CONFIRM = A and B
B_ONLY_SAFE     = B and not A
A_ONLY_OBSERVE  = A and not B
```

## Signal IDs

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_CORE_AB_CONFIRM_FIXED10_RR2_12H
GOLD_H1H4_BEAR_M15_LOW_BREAK_B_ONLY_SAFE_FIXED10_RR2_12H
GOLD_H1H4_BEAR_M15_LOW_BREAK_A_ONLY_OBSERVE_FIXED10_RR2_12H
```

## Trade handling

```text
CORE_AB_CONFIRM:
  trade_enabled = true
  lot_multiplier = 2.0

B_ONLY_SAFE:
  trade_enabled = true
  lot_multiplier = 1.0

A_ONLY_OBSERVE:
  trade_enabled = false
  lot_multiplier = 0.0
```

## Entry/exit

```text
direction = SELL
entry_time = next M15 open time
entry_price = next M15 open
SL = entry + 10.0
TP = entry - 20.0
RR = 2.0
max_hold = 12h
M1 first-touch
same M1 bar conflict = SL priority
```

Live dry-run uses latest confirmed M15 close/current reference if the next M15 open is not present yet.

## Cooldown

```text
cooldown_bars_m15 = 8
cooldown_minutes = 120
```

Common cooldown across trade-enabled CORE and B_ONLY.

## Implemented files

### Design doc

```text
docs/GOLD_H1H4_BEAR_AB_CLASSIFIER_DESIGN.md
```

### Research/backtest script

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

## Live scan once command

```cmd
python scripts\run_gold_h1h4_bear_ab_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan
```

If the last M15 row is the forming candle:

```cmd
python scripts\run_gold_h1h4_bear_ab_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan --latest-confirmed-policy second_last
```

## Uploaded CSV validation result in the implementation chat

Using the uploaded CSV set and the common cooldown implementation:

```text
raw signals: 354
trade-enabled raw signals: 349
cooldown trades: 68
```

By rank:

```text
B_ONLY_SAFE:
  trades: 46
  wins: 25
  losses: 21
  WR: 54.35%
  total R: +29R
  PF: 2.38
  max DD: 5R

CORE_AB_CONFIRM:
  trades: 22
  wins: 13
  losses: 9
  WR: 59.09%
  total R: +17R
  lot-weighted R: +34R
  PF: 2.89
  max DD: 2R
```

Combined:

```text
trades: 68
wins: 38
losses: 30
WR: 55.88%
total R unweighted: +46R
total R lot-weighted: +63R
PF unweighted: 2.53
PF lot-weighted: 2.62
max DD unweighted: 5R
max DD lot-weighted: 6R
```

2026-04-28 07:00-14:00 MT5 time:

```text
CORE_AB_CONFIRM
entry_time: 2026-04-28 08:15:00
entry: 4652.40
SL: 4662.40
TP: 4632.40
outcome: WIN
realized: +2R
lot_multiplier: 2.0
lot-weighted: +4R
```

Note: this result uses a unified classifier with common cooldown. It differs from earlier exploratory overlap stats because those compared A and B as separate candidate lists.

## Next recommended steps

1. Run the research command on the live MT5 CSV directory.
2. Inspect:
   ```text
   summary_by_rank.csv
   summary_overall_lot_weighted.csv
   monthly_by_rank.csv
   target_window_20260428.csv
   ```
3. Run the live scan once.
4. Inspect:
   ```text
   latest_scan_result.json
   latest_signal_payload.json
   order_intent_dry_run.json
   notification_preview_latest.txt
   signal_ledger.csv
   ```
5. If dry-run scan and ledger duplicate behavior are OK, next build a small loop wrapper.
6. Do not connect this family to demo autotrade until the dry-run lifecycle is reviewed.

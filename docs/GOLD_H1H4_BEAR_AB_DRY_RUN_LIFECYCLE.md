# GOLD H1/H4 Bearish A/B Classifier Dry-Run Lifecycle

## Purpose

This document records the isolated dry-run lifecycle added for the GOLD/XAUUSD SELL-side H1/H4 bearish A/B classifier.

It is intentionally separated from:

- BUY-side GOLD C_ENV RR2 72h dry-run outputs
- Existing Mochipoyo live/demo/autotrade flow
- Discord real send
- Real MT5 order placement
- Existing autotrade order-intent files

## Strategy family

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

## Signal IDs

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_CORE_AB_CONFIRM_FIXED10_RR2_12H
GOLD_H1H4_BEAR_M15_LOW_BREAK_B_ONLY_SAFE_FIXED10_RR2_12H
GOLD_H1H4_BEAR_M15_LOW_BREAK_A_ONLY_OBSERVE_FIXED10_RR2_12H
```

## Rank handling

```text
CORE_AB_CONFIRM:
  A and B
  trade_enabled = true
  lot_multiplier = 2.0

B_ONLY_SAFE:
  B and not A
  trade_enabled = true
  lot_multiplier = 1.0

A_ONLY_OBSERVE:
  A and not B
  trade_enabled = false
  lot_multiplier = 0.0
```

A and B are normalized to one final signal per M15 bar.

## Added scripts

### Research/backtest

```text
scripts/research_gold_h1h4_bear_m15_low_break_ab_classifier.py
```

### Signal review / notification preview / order intent preview

```text
scripts/research_gold_h1h4_bear_ab_notification_and_intent_preview.py
```

### Live scan once

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
```

### Position monitor once

```text
scripts/run_gold_h1h4_bear_ab_position_monitor_once.py
```

### Combined dry-run cycle runner

```text
scripts/run_gold_h1h4_bear_ab_dry_run_cycle.py
```

## SELL-specific monitor rules

```text
Direction: SELL
TP is below entry
SL is above entry
TP touch: M5 low <= tp_price
SL touch: M5 high >= sl_price
Same M5 TP/SL conflict: SL priority by default
R calculation: (entry_price - exit_price) / risk_price
close_side for close intent: BUY
```

## Dedicated output directory

```text
data/research_results/gold_h1h4_bear_ab_live_scan/
```

Expected dry-run outputs:

```text
latest_scan_result.json
latest_signal_payload.json                 only when a signal/observe row is detected
order_intent_dry_run.json                  only when a signal/observe row is detected
notification_preview_latest.txt            only when a signal/observe row is detected
live_scan_log.csv
signal_ledger.csv
latest_position_monitor_result.json
latest_position_monitor_rows.csv
position_monitor_log.csv
close_intent_log.csv
close_intent_dry_run.json                  only when TIME_EXIT close intent is created
latest_dry_run_cycle_result.json
dry_run_cycle_log.csv
dry_run_cycle_command_logs/
```

## Commands

### Research/backtest

```cmd
python scripts\research_gold_h1h4_bear_m15_low_break_ab_classifier.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_m15_low_break_ab_classifier
```

### Preview export

```cmd
python scripts\research_gold_h1h4_bear_ab_notification_and_intent_preview.py --input-csv data\research_results\gold_h1h4_bear_m15_low_break_ab_classifier\trades_classified_cooldown.csv
```

### Live scan once

```cmd
python scripts\run_gold_h1h4_bear_ab_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan
```

If the M15 CSV includes a forming candle as the last row:

```cmd
python scripts\run_gold_h1h4_bear_ab_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan --latest-confirmed-policy second_last
```

### Position monitor once

```cmd
python scripts\run_gold_h1h4_bear_ab_position_monitor_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan
```

If the M5 CSV includes a forming candle as the last row:

```cmd
python scripts\run_gold_h1h4_bear_ab_position_monitor_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan --latest-confirmed-m5-policy second_last
```

### Combined dry-run cycle

```cmd
python scripts\run_gold_h1h4_bear_ab_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan
```

### Repeated 15-minute dry-run cycle

```cmd
python scripts\run_gold_h1h4_bear_ab_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_h1h4_bear_ab_live_scan --cycles 0 --sleep-seconds 900
```

Use Ctrl+C to stop an infinite loop.

## Important implementation note

The live scan script was adjusted so the latest confirmed M15 bar can be evaluated even when the next M15 open row is not yet present in the CSV.

Backtest still uses:

```text
entry_price = next M15 open
```

Live dry-run uses:

```text
entry_price_reference = latest confirmed M15 close
```

when next M15 open is unavailable.

## Validation status

The scripts have been added to GitHub. They still need to be run on the user's local Windows/MT5 CSV directory for runtime validation.

Recommended validation order:

```text
1. research/backtest command
2. preview export command
3. live scan once command
4. position monitor once command
5. combined dry-run cycle command
6. inspect latest_dry_run_cycle_result.json
```

Do not connect this strategy to Mochipoyo or demo autotrade until the dry-run cycle output is reviewed.

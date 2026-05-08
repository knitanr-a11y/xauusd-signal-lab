# GOLD C_ENV RR2 72h Signal Design

## Purpose

This document records the current research candidate for a GOLD/XAUUSD BUY signal that may later be used for notification and demo autotrade dry-run validation.

The logic is intentionally separated from the existing Mochipoyo live/demo/autotrade flow until dry-run validation is complete.

## Current candidate ID

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

## Separation policy

This candidate must not be mixed directly into existing Mochipoyo live/autotrade scripts yet.

Do not write to:

- existing Mochipoyo trigger state
- existing Mochipoyo notification ledger
- existing autotrade order-intent files
- Discord webhook output
- MT5 source candle CSVs

Use research/dry-run output directories until explicitly promoted.

## Data policy

For research/backtest validation, use copied CSV snapshots, for example:

```text
data/research_csv_snapshots/gold_cb_20260508_01/
```

For live dry-run scanning, read the MT5 live CSV directory but only write dry-run outputs under:

```text
data/research_results/gold_c_env_rr2_72h_live_scan/
```

## Required CSV files

The logic expects the following GOLD CSV files:

```text
goldsharp_h4.csv
goldsharp_h1.csv
goldsharp_m15.csv
goldsharp_m5.csv
```

Required columns:

```text
time, open, high, low, close
```

Optional columns:

```text
tick_volume, spread, real_volume
```

## Indicator settings

All MACD calculations use:

```text
Fast EMA: 6
Slow EMA: 13
Signal: 4
```

Other indicators:

```text
EMA20
EMA50
ATR14
MACD
MACD signal
MACD histogram
```

close_time is assigned by timeframe:

```text
H4  = time + 4h
H1  = time + 1h
M15 = time + 15m
M5  = time + 5m
```

## H4 condition: C_ENV

H4 is used as an environment permission filter.

The latest confirmed H4 candle at the M15 signal close time must satisfy:

```text
H4 ema20 > H4 ema50
H4 close > H4 ema50
```

Important:

```text
H4 regular bullish divergence is NOT required for this candidate.
H4 env_up and H4 strict divergence must not be mixed under the same condition ID.
```

## H1 condition: regular bullish divergence

Use pivot lows with:

```text
left = 2
right = 2
```

A pivot is usable only after confirmation:

```text
pivot_confirm_idx = pivot_idx + right
pivot_confirm_time = close_time[pivot_confirm_idx]
```

Regular bullish divergence:

```text
current_pivot_low < previous_pivot_low
current_pivot_macd > previous_pivot_macd
```

Loose exhaustion filter:

```text
H1 close_at_confirm < H1 ema50_at_confirm
OR
H1 ema20_at_confirm < H1 ema50_at_confirm
```

## M15 trigger

After an H1 regular bullish event is confirmed, search for the first M15 trigger within:

```text
12 hours
```

M15 trigger rules:

```text
M15 close > high.shift(1).rolling(8).max()
M15 close > M15 ema20
M15 MACD > M15 MACD signal
M15 MACD histogram > previous M15 MACD histogram
```

This is called BO8 in file names and condition names.

## Entry

BUY only.

```text
entry_time = M15 close_time
entry_price_reference = M15 close
entry_type = MARKET_ON_SIGNAL
```

## Stop loss

Current preferred SL:

```text
SL = H1 regular bullish pivot low - M15 ATR14 * 0.05
```

This performed better than the earlier M15 lower12 SL.

## Take profit

```text
TP = entry_price + (entry_price - SL) * 2.0
RR = 2.0
```

## Exit rule

```text
TP/SL first-touch
If neither TP nor SL is reached within 72h, exit at the last M5 close before the 72h horizon.
```

Same M5 candle TP/SL conflict:

```text
SL priority
```

## M5 coverage rule

This is critical.

If a trade entry time is earlier than the first available M5 candle, it must be treated as:

```text
NO_M5_PATH
```

No-timeout or hold-horizon evaluation must never skip missing M5 history and judge old entries using later M5 data.

## Research result snapshot

Using the copied snapshot `gold_cb_20260508_01`, the preferred 72h setup had:

```text
trades: 7
wins: 4
losses: 0
time exits: 3
total R: about +9.39R
max DD: about 0.45R
```

72h was preferred over no-timeout because no-timeout reached about +11R but allowed a maximum hold of about 213.5 hours, which is too long for the intended practical flow.

## Individual 72h result behavior

The four WIN trades reached TP within 72h. The remaining three were TIME_EXITs:

```text
2025-12-02/05 area: TIME_EXIT positive
2026-01 area: TIME_EXIT positive
2026-02 area: TIME_EXIT negative but smaller than full -1R
2026-04 trades: fast TP wins
```

The 72h cap is useful because it limits long unresolved positions and reduced the 2026-02 loss from a full SL loss to a smaller time-exit loss in the research comparison.

## Main scripts created during this phase

### Strict H4 divergence baseline

```text
scripts/research_gold_c_strict_h1_regular_bullish_m15_break.py
```

Result: too few trades under strict H4 divergence-only permission.

### H4 permission comparison

```text
scripts/research_gold_h4_permission_modes_h1_regular_bullish_m15_break.py
```

Compared:

```text
C_STRICT
C_ENV
C_STRICT_OR_ENV
```

Finding: C_ENV was the source of the useful behavior, not C_STRICT.

### C_ENV RR2 entry-window no-timeout comparison

```text
scripts/research_gold_c_env_rr2_entry_window_no_timeout.py
```

Fixed M5 coverage bug so entries before M5 history start become NO_M5_PATH.

Finding: 12h, 24h, and 36h all had the same evaluated trades after M5 coverage correction. 12h was preferred because it is tighter.

### SL and breakout grid

```text
scripts/research_gold_c_env_rr2_sl_breakout_grid_no_timeout.py
```

Compared:

```text
BO8 vs BO12
M15 lower12 SL vs H1 pivot SL
```

Finding: H1 pivot SL was better; BO8 and BO12 were effectively the same. BO8 was kept.

### Hold-time analysis

```text
scripts/research_gold_c_env_rr2_best_hold_time_analysis.py
```

Finding: no-timeout worked but could hold too long.

### Hold-horizon comparison

```text
scripts/research_gold_c_env_rr2_best_hold_horizon_compare.py
```

Finding: 72h was the best practical balance.

### Signal review export

```text
scripts/research_gold_c_env_rr2_72h_signal_review_export.py
```

Creates:

```text
data/research_results/gold_c_env_rr2_best_hold_horizon_compare/signal_review_72h.csv
```

### Notification and dry-run intent preview

```text
scripts/research_gold_c_env_rr2_72h_notification_and_intent_preview.py
```

Creates:

```text
notification_preview_72h.txt
notification_preview_72h.csv
order_intent_preview_72h.jsonl
order_intent_preview_72h.csv
```

### Live dry-run scanner once

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
```

Reads live CSVs and checks only the latest confirmed M15 signal point.

Outputs dry-run files only:

```text
data/research_results/gold_c_env_rr2_72h_live_scan/latest_scan_result.json
data/research_results/gold_c_env_rr2_72h_live_scan/latest_signal_payload.json
data/research_results/gold_c_env_rr2_72h_live_scan/order_intent_dry_run.json
data/research_results/gold_c_env_rr2_72h_live_scan/notification_preview_latest.txt
data/research_results/gold_c_env_rr2_72h_live_scan/live_scan_log.csv
data/research_results/gold_c_env_rr2_72h_live_scan/signal_ledger.csv
```

## Latest live dry-run scan status

The latest uploaded dry-run result showed:

```text
candidate_count: 24
latest_candidate_entry_time: 2026-04-17 07:45:00
latest_m15_close_time: 2026-05-08 12:30:00
signal_found: false
reason: NO_SIGNAL_ON_LATEST_CONFIRMED_M15
```

So the scanner is working and correctly did not emit a signal on the latest confirmed M15 bar.

## Next implementation steps

1. Keep the candidate separated from Mochipoyo live/autotrade.
2. Add or run more live dry-run scans over time.
3. Confirm whether the live CSV uses the last row as confirmed or includes a forming candle. If it includes a forming candle, run with:

```cmd
--latest-confirmed-policy second_last
```

4. Add a dedicated 72h position-monitor dry-run before any autotrade integration.
5. Only after live scan dry-run, duplicate ledger, order-intent dry-run, and position-monitor dry-run pass should this be connected to demo autotrade.

# NEXT CHAT HANDOFF - GOLD C_ENV RR2 72H

Use this as the first document to read in the next chat.

## Repository

```text
knitanr-a11y/xauusd-signal-lab
```

## Read these first

```text
docs/GOLD_C_ENV_RR2_72H_SIGNAL_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_C_ENV_RR2_72H.md
```

## Current objective

Continue the GOLD/XAUUSD signal candidate that has been researched as:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

The goal is to proceed toward notification and demo autotrade dry-run integration, while keeping this candidate separated from the existing Mochipoyo live/autotrade flow until validation passes.

## Current signal logic

BUY only.

### H4 environment

Latest confirmed H4 candle at the M15 signal time must satisfy:

```text
ema20 > ema50
close > ema50
```

This is `C_ENV`.

Do not mix with `C_STRICT` H4 regular bullish divergence under the same condition ID.

### H1 setup

H1 regular bullish divergence using pivot lows:

```text
pivot_left = 2
pivot_right = 2
current_pivot_low < previous_pivot_low
current_pivot_macd > previous_pivot_macd
```

Loose exhaustion condition:

```text
close_at_confirm < ema50_at_confirm
OR
ema20_at_confirm < ema50_at_confirm
```

### M15 trigger

Search for first M15 trigger within 12h after H1 divergence confirmation:

```text
close > high.shift(1).rolling(8).max()
close > ema20
MACD(6,13,4) > signal
macd_hist > previous macd_hist
```

### Entry / SL / TP / exit

```text
Entry = M15 close at M15 close_time
SL = H1 pivot low - M15 ATR14 * 0.05
TP = entry + (entry - SL) * 2.0
RR = 2.0
Max hold = 72h
```

Exit rule:

```text
TP/SL first-touch by M5
same M5 bar TP/SL conflict = SL priority
if unresolved by 72h, exit at the last M5 close before 72h
```

## Important M5 coverage rule

If entry_time is earlier than the first available M5 candle:

```text
NO_M5_PATH
```

Never skip months of missing M5 data and evaluate an old entry using later M5 candles.

This bug was found and fixed in:

```text
scripts/research_gold_c_env_rr2_entry_window_no_timeout.py
```

## Research summary

Using copied snapshot:

```text
data/research_csv_snapshots/gold_cb_20260508_01/
```

The preferred 72h setup produced approximately:

```text
trades: 7
wins: 4
losses: 0
time exits: 3
total R: +9.39R
max DD: about 0.45R
```

No-timeout produced more total R but allowed a maximum hold around 213.5h, so 72h is preferred as the practical version.

## Key files/scripts created

### Design doc

```text
docs/GOLD_C_ENV_RR2_72H_SIGNAL_DESIGN.md
```

### H4 permission comparison

```text
scripts/research_gold_h4_permission_modes_h1_regular_bullish_m15_break.py
```

Finding: `C_ENV` was the useful permission mode; `C_STRICT` was too sparse.

### C_ENV RR2 entry-window no-timeout

```text
scripts/research_gold_c_env_rr2_entry_window_no_timeout.py
```

Finding: after M5 coverage correction, 12h / 24h / 36h had the same evaluated trades. 12h was preferred because it is tighter.

### SL/breakout grid

```text
scripts/research_gold_c_env_rr2_sl_breakout_grid_no_timeout.py
```

Finding: H1 pivot SL was better than M15 lower12 SL. BO8 and BO12 were effectively the same; BO8 kept.

### Hold-time / horizon comparison

```text
scripts/research_gold_c_env_rr2_best_hold_time_analysis.py
scripts/research_gold_c_env_rr2_best_hold_horizon_compare.py
```

Finding: 72h hold cap is the best practical balance.

### Signal review export

```text
scripts/research_gold_c_env_rr2_72h_signal_review_export.py
```

Creates:

```text
data/research_results/gold_c_env_rr2_best_hold_horizon_compare/signal_review_72h.csv
```

### Notification and order-intent preview

```text
scripts/research_gold_c_env_rr2_72h_notification_and_intent_preview.py
```

Creates:

```text
data/research_results/gold_c_env_rr2_best_hold_horizon_compare/notification_preview_72h.txt
data/research_results/gold_c_env_rr2_best_hold_horizon_compare/notification_preview_72h.csv
data/research_results/gold_c_env_rr2_best_hold_horizon_compare/order_intent_preview_72h.jsonl
data/research_results/gold_c_env_rr2_best_hold_horizon_compare/order_intent_preview_72h.csv
```

### Live dry-run scan once

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
```

This reads the live MT5 CSV directory and checks the latest confirmed M15 bar only. It writes only dry-run outputs under:

```text
data/research_results/gold_c_env_rr2_72h_live_scan/
```

It does not send Discord messages or place orders.

## Latest live scan result

The uploaded latest scan result was:

```json
{
  "candidate_count": 24,
  "condition_id": "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H",
  "duplicate": false,
  "latest_candidate_entry_time": "2026-04-17 07:45:00",
  "latest_m15_close_time": "2026-05-08 12:30:00",
  "reason": "NO_SIGNAL_ON_LATEST_CONFIRMED_M15",
  "scan_time_utc": "2026-05-08 09:43:19",
  "signal_found": false
}
```

This means the scanner ran successfully and did not emit a new signal on the latest confirmed M15 bar.

## Last GitHub commits in this phase

```text
db35ca561a078451b6b5a4accda7e7f7fcd06941  Add GOLD C_ENV RR2 72h signal design document
5c759da6e2c8632ad76447833f8ee39c6528417d  Fix Windows path escape in live scan docstring
1ed24b5e160e360adf5a4278f309b55553ccda76  Add dry-run live scan once for C_ENV RR2 72h setup
5b2c6f2be8b2a06dc08f1f03fb1051878b30c7c2  Add notification and intent preview for C_ENV RR2 72h setup
```

## Important implementation notes

1. The live scan script originally had a Python unicodeescape error because the docstring included a Windows path with `C:\Users\...`. It was fixed by using a raw docstring.
2. Keep this candidate isolated from Mochipoyo until the dry-run lifecycle is validated.
3. The next required component for autotrade readiness is a dedicated position monitor dry-run for 72h time exits.

## Recommended next steps

### Step 1: Continue live dry-run scans

Run:

```cmd
python scripts\run_gold_c_env_rr2_72h_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
```

If the MT5 CSV includes the currently forming M15 candle as the last row, use:

```cmd
--latest-confirmed-policy second_last
```

### Step 2: Inspect outputs

Check:

```cmd
type data\research_results\gold_c_env_rr2_72h_live_scan\latest_scan_result.json
```

If a signal appears, also check:

```cmd
type data\research_results\gold_c_env_rr2_72h_live_scan\notification_preview_latest.txt
type data\research_results\gold_c_env_rr2_72h_live_scan\order_intent_dry_run.json
```

### Step 3: Build position monitor dry-run

Next script to create:

```text
scripts/run_gold_c_env_rr2_72h_position_monitor_once.py
```

Initial dry-run role:

```text
read dedicated signal_ledger.csv
find DRY_RUN_SIGNAL_CREATED rows
check entry_time + 72h
if expired, write close_intent_dry_run.json or close_intent_log.csv
no MT5 close order yet
```

### Step 4: Only after dry-run PASS

Only after these pass:

```text
live scan dry-run
signal ledger duplicate filter
notification preview
order intent dry-run
position monitor dry-run
```

then consider connecting to demo autotrade. Do not connect directly to existing Mochipoyo autotrade without a separate review.

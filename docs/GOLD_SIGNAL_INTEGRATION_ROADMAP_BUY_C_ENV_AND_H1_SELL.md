# GOLD Signal Integration Roadmap - BUY C_ENV 72h and H1 SELL

## Purpose

This document records the integration plan for multiple GOLD/XAUUSD signal candidates before connecting them to demo autotrade.

The current completed-side candidate is the BUY-side setup:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

A separate H1 down / SELL signal is being designed next. The important decision is:

```text
Do not integrate either candidate directly into existing Mochipoyo live/demo/autotrade yet.
Complete and validate each candidate in its own isolated dry-run lifecycle first.
Then integrate through a dedicated strategy router.
```

## Current status summary

### BUY-side C_ENV RR2 72h candidate

Status:

```text
Research/backtest: PASS as a sparse candidate
Notification preview: PASS
Order intent preview: PASS
Live scan once: PASS
Position monitor once: PASS
Combined dry-run cycle runner: PASS
No-signal / no-position path: PASS
Existing Mochipoyo integration: NOT CONNECTED
Demo autotrade order placement: NOT CONNECTED
Discord real send: NOT CONNECTED
```

Latest condition ID:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

Core logic:

```text
BUY only
H4 C_ENV: latest confirmed H4 ema20 > ema50 and close > ema50
H1 regular bullish divergence: current pivot low < previous pivot low and current pivot MACD > previous pivot MACD
H1 loose exhaustion: close < ema50 OR ema20 < ema50 at H1 pivot confirmation
M15 trigger: first BO8 trigger within 12h after H1 confirmation
Entry: M15 close
SL: H1 pivot low - M15 ATR14 * 0.05
TP: RR2.0
Exit: M5 first-touch, SL priority on same-M5 TP/SL conflict, 72h TIME_EXIT if unresolved
```

Important M5 coverage rule:

```text
If entry_time is earlier than first available M5 candle, outcome must be NO_M5_PATH.
Never skip missing M5 periods and judge old entries using later M5 data.
```

### Latest BUY-side live dry-run result

The latest combined dry-run cycle completed successfully:

```text
cycle_ok: true
live_scan_returncode: 0
position_monitor_returncode: 0
```

Live scan result in that cycle:

```text
candidate_count: 24
latest_candidate_entry_time: 2026-04-17 07:45:00
latest_m15_close_time: 2026-05-08 13:00:00
signal_found: false
reason: NO_SIGNAL_ON_LATEST_CONFIRMED_M15
```

Position monitor result in that cycle:

```text
signals_monitored: 0
close_intent_created: 0
reason: NO_DRY_RUN_SIGNAL_CREATED_ROWS
```

Interpretation:

```text
The dry-run framework is functioning correctly.
No new BUY signal existed on the latest confirmed M15 bar.
Because no dry-run signal was created, there was no position to monitor and no close intent to create.
```

## BUY-side files already created

### Design / handoff docs

```text
docs/GOLD_C_ENV_RR2_72H_SIGNAL_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_C_ENV_RR2_72H.md
```

### Research scripts

```text
scripts/research_gold_h4_permission_modes_h1_regular_bullish_m15_break.py
scripts/research_gold_c_env_rr2_entry_window_no_timeout.py
scripts/research_gold_c_env_rr2_sl_breakout_grid_no_timeout.py
scripts/research_gold_c_env_rr2_best_hold_time_analysis.py
scripts/research_gold_c_env_rr2_best_hold_horizon_compare.py
scripts/research_gold_c_env_rr2_72h_signal_review_export.py
scripts/research_gold_c_env_rr2_72h_notification_and_intent_preview.py
```

### Live dry-run scripts

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
scripts/run_gold_c_env_rr2_72h_position_monitor_once.py
scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
```

### BUY-side dry-run output directory

```text
data/research_results/gold_c_env_rr2_72h_live_scan/
```

Expected files under the dry-run output directory:

```text
latest_scan_result.json
latest_signal_payload.json                 only when a new signal is created
order_intent_dry_run.json                  only when a new signal is created
notification_preview_latest.txt            only when a new signal is created
live_scan_log.csv
signal_ledger.csv
latest_position_monitor_result.json
latest_position_monitor_rows.csv
position_monitor_log.csv
close_intent_log.csv
close_intent_dry_run.json                  only when a TIME_EXIT close intent is created
latest_dry_run_cycle_result.json
dry_run_cycle_log.csv
dry_run_cycle_command_logs/
```

## Commands for the BUY-side dry-run flow

### Single live scan only

```cmd
python scripts\run_gold_c_env_rr2_72h_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
```

If the M15 CSV includes a forming candle as the last row:

```cmd
python scripts\run_gold_c_env_rr2_72h_live_scan_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan --latest-confirmed-policy second_last
```

### Single position monitor only

```cmd
python scripts\run_gold_c_env_rr2_72h_position_monitor_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
```

If the M5 CSV includes a forming candle as the last row:

```cmd
python scripts\run_gold_c_env_rr2_72h_position_monitor_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan --latest-confirmed-m5-policy second_last
```

### Combined single dry-run cycle

```cmd
python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
```

### Repeated 15-minute dry-run cycle

This does not end automatically. Stop with Ctrl+C.

```cmd
python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan --cycles 0 --sleep-seconds 900
```

For limited tests, prefer finite cycles:

```cmd
python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan --cycles 4 --sleep-seconds 900
```

## Why H1 SELL should be completed before integration

The BUY-side candidate has reached a stable isolated dry-run base. However, connecting it to demo autotrade before the H1 SELL candidate is designed would force a second integration pass later.

Recommended approach:

```text
1. Freeze BUY-side C_ENV 72h as isolated dry-run PASS.
2. Build H1 SELL signal separately.
3. Validate H1 SELL with the same research/dry-run lifecycle.
4. Only then create a shared strategy router.
5. Only after the router passes, connect to demo autotrade dry-run.
```

This avoids mixing incomplete logic into the existing live/demo/autotrade flow.

## Required lifecycle for the upcoming H1 SELL signal

The H1 SELL candidate should go through the same phases as the BUY-side setup.

### Phase 1: Research / backtest

Required:

```text
- Define exact condition ID
- Confirm timeframe rules
- Confirm MACD settings
- Confirm pivot rules
- Confirm entry trigger
- Confirm SL / TP / RR
- Confirm M5 first-touch outcome rule
- Confirm same-M5 TP/SL conflict rule
- Confirm max hold / time exit rule
- Confirm NO_M5_PATH handling
```

For SELL, pay special attention to direction reversal:

```text
Entry: SELL
TP is below entry
SL is above entry
TP first-touch uses M5 low <= tp_price
SL first-touch uses M5 high >= sl_price
R calculation is (entry_price - exit_price) / risk_price
close_side for a SELL position is BUY
```

### Phase 2: Signal review export

The H1 SELL setup should produce a review CSV similar to the BUY-side `signal_review_72h.csv`.

Recommended minimum columns:

```text
condition_id
symbol
direction
entry_time
entry_price
sl_price
tp_price
risk_price
rr
max_hold_hours
outcome
realized_r
exit_time
exit_price
hold_hours
h1/h4/m15 context columns used by the signal
```

### Phase 3: Notification preview and order-intent preview

The H1 SELL setup should create:

```text
notification_preview_*.txt
notification_preview_*.csv
order_intent_preview_*.jsonl
order_intent_preview_*.csv
```

The order intent schema can be strategy-specific at first, but should include fields compatible with a later shared router:

```text
schema_version
condition_id
strategy_id
symbol
direction
entry_type
signal_time
entry_price_reference
sl_price
tp_price
risk_price
rr
max_hold_hours
time_exit_required
risk_mode
lot / volume placeholder
dry_run
source_signal
```

### Phase 4: Live scan once

The H1 SELL setup should have its own isolated script, for example:

```text
scripts/run_gold_h1_sell_*_live_scan_once.py
```

It should write to its own dry-run output directory, for example:

```text
data/research_results/gold_h1_sell_*_live_scan/
```

It must not write to the BUY-side ledger or outputs.

Required output shape:

```text
latest_scan_result.json
latest_signal_payload.json       only when a signal is created
order_intent_dry_run.json        only when a signal is created
notification_preview_latest.txt  only when a signal is created
live_scan_log.csv
signal_ledger.csv
```

The H1 SELL `latest_scan_result.json` should include at least:

```text
scan_time_utc
condition_id
signal_found
duplicate
reason
latest_confirmed_signal_time or latest_base_close_time
candidate_count
latest_candidate_entry_time
signal_key when applicable
outputs when applicable
```

### Phase 5: Position monitor once

The H1 SELL setup should have its own isolated monitor, for example:

```text
scripts/run_gold_h1_sell_*_position_monitor_once.py
```

It should read only the H1 SELL dedicated `signal_ledger.csv`.

Required output shape:

```text
latest_position_monitor_result.json
latest_position_monitor_rows.csv
position_monitor_log.csv
close_intent_log.csv
close_intent_dry_run.json only when close intent is created
```

For SELL positions:

```text
TP touch: M5 low <= tp_price
SL touch: M5 high >= sl_price
same-M5 conflict: use configured priority, default should remain conservative
TIME_EXIT realized R: (entry_price - exit_price) / risk_price
close_side: BUY
```

### Phase 6: H1 SELL dry-run cycle runner

The H1 SELL setup should have a combined runner similar to BUY-side:

```text
scripts/run_gold_h1_sell_*_dry_run_cycle.py
```

It should run:

```text
1. H1 SELL live scan once
2. H1 SELL position monitor once
```

and write:

```text
latest_dry_run_cycle_result.json
dry_run_cycle_log.csv
dry_run_cycle_command_logs/
```

## Later integration design: strategy router

After BUY C_ENV 72h and H1 SELL both pass isolated dry-run, create a shared router instead of modifying the existing Mochipoyo flow directly.

Possible script name:

```text
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

Initial router role:

```text
Run each strategy dry-run cycle once
Collect each latest_dry_run_cycle_result.json
Normalize summary fields
Write a combined router result JSON/CSV
Do not place orders
Do not send Discord
Do not write existing Mochipoyo ledgers
```

Possible router output directory:

```text
data/research_results/gold_multi_strategy_dry_run/
```

Possible router outputs:

```text
latest_multi_strategy_cycle_result.json
multi_strategy_cycle_log.csv
strategy_status_latest.csv
combined_order_intent_dry_run.jsonl
combined_close_intent_dry_run.jsonl
```

At this stage, the router should only copy or reference the strategy-specific dry-run intents. It should not yet create real order requests.

## Later integration design: demo autotrade dry-run

Only after both strategy-specific dry-run cycles and the multi-strategy router pass should demo autotrade integration be considered.

Before demo autotrade, confirm:

```text
- Duplicate signal prevention works for each strategy
- Duplicate close intent prevention works for each strategy
- BUY and SELL signal keys do not collide
- Strategy IDs are unique
- Order intents have consistent schema
- Close intents have consistent schema
- Time exits are represented consistently
- M5 coverage gaps remain NO_M5_PATH
- No script writes to live MT5 source CSVs
- No strategy uses a forming candle unless explicitly intended
```

## Current recommendation

Do this next:

```text
1. Pause further BUY-side integration work.
2. Build and validate the H1 SELL signal in isolation.
3. Use this document as the integration target for the H1 SELL side.
4. After H1 SELL reaches dry-run cycle PASS, create the multi-strategy router.
```

The BUY-side C_ENV 72h candidate should remain available for live dry-run observation, but it should not be connected to demo autotrade yet.

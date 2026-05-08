# GOLD multi-strategy demo dry-run integration design

Last updated: 2026-05-08

## Purpose

This document defines the safe integration path from isolated BUY/SELL strategy dry-runs into a multi-strategy demo autotrade dry-run pipeline.

The goal is to create a new multi-strategy dry-run loop that can run beside the existing Mochipoyo demo autotrade loop design, without changing the existing production-like BAT or calling `mt5.order_send`.

## Current validated chain

The validated chain is:

```text
BUY/SELL isolated strategy runners
  ↓
scripts/run_gold_multi_strategy_dry_run_cycle.py
  ↓
scripts/run_gold_multi_strategy_autotrade_adapter_dry_run.py
  ↓
scripts/build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py
  ↓
scripts/send_mt5_order_from_payload.py WITHOUT --send
```

## Current safety validation status

### Router

```text
BUY/SELL no-signal aggregation: PASS
strategy status aggregation: PASS
order intent aggregation: PASS
close intent aggregation: PASS
aggregate-only mode: PASS
```

### Adapter

```text
adapter preview creation: PASS
adapter duplicate preview ledger: PASS
adapter empty ledger CSV handling: PASS
OPEN_POSITION preview: PASS
CLOSE_POSITION preview: PASS
rejects: 0 in validated TIME_EXIT case
```

### Mochipoyo-compatible payload bridge

Script:

```text
scripts/build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py
```

Validated with SELL TIME_EXIT aggregate-only case:

```text
bridge_ok: true
rows_in: 1
rows_out: 1
valid_order_payloads: 1
rejects: 0
broker_symbol: GOLD#
fixed_lot: 0.01
use_adapter_lot: false
magic: 26050601
```

Generated order payload:

```text
order_status: DRY_RUN_READY
broker_symbol: GOLD#
direction: SELL
lot: 0.01
entry_price_reference: 5025.38
sl_price: 5035.38
tp_price: 5005.38
rr: 2.0
candidate_rank: B_ONLY_SAFE
pair_name: SELL_H1H4_BEAR_AB
```

### MT5 sender dry-run / position guard

Script:

```text
scripts/send_mt5_order_from_payload.py
```

Validation command used WITHOUT `--send`:

```cmd
python scripts\send_mt5_order_from_payload.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\order_payloads.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\mt5_order_check_dry_run --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --require-demo-account --position-policy block_any --max-symbol-positions 1 --max-symbol-lot 0.01
```

Observed result with an existing GOLD# demo position:

```text
send_requested: False
account_login: 75539039
account_server: XMTrading-MT5 3
account_name: Demo Account
terminal_trade_allowed: True
account_trade_allowed: True
position_policy: block_any
max_symbol_positions: 1
max_symbol_lot: 0.01
order_send_called_count: 0
dry_run_check_ok_rows: 0
sent_rows: 0
blocked_position_policy_rows: 1
error_rows: 1
existing_symbol_positions: 1
existing_symbol_lot: 0.01
existing_symbol_directions: BUY
order_status: BLOCKED_POSITION_POLICY
validation_errors: position policy block_any blocked order: existing_positions=1; existing_lot=0.01
```

Decision:

```text
MT5 sender dry-run / block_any guard: PASS
Existing-position safety block: PASS
order_send was not called: PASS
```

`error_rows: 1` is expected in this case because `send_mt5_order_from_payload.py` counts `BLOCKED_*` rows as error rows in the report. This is not a dangerous execution error. The key safety result is:

```text
order_send_called_count: 0
sent_rows: 0
```

### One-cycle multi-strategy demo dry-run runner

Script:

```text
scripts/run_gold_multi_strategy_demo_dry_run_cycle.py
```

Validated command pattern:

```cmd
python scripts\run_gold_multi_strategy_demo_dry_run_cycle.py --csv-dir "<MT5_FILES_DIR>" --out-dir data\research_results\gold_multi_strategy_demo_dry_run_cycle --router-out-dir data\research_results\gold_multi_strategy_dry_run --buy-out-dir data\research_results\gold_c_env_rr2_72h_live_scan --sell-out-dir data\research_results\gold_h1h4_bear_ab_live_loop --adapter-out-dir data\research_results\gold_multi_strategy_autotrade_adapter_dry_run --payload-out-dir data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run --mt5-dry-run-out-dir data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\mt5_order_check_dry_run --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --broker-symbol GOLD# --fixed-lot 0.01 --magic 26050601 --expected-login 75539039 --position-policy block_any --max-symbol-positions 1 --max-symbol-lot 0.01 --max-orders 1
```

Validated result on latest no-signal cycle:

```text
cycle_ok: true
safe_no_send: true
router_returncode: 0
adapter_returncode: 0
payload_bridge_returncode: 0
mt5_dry_run_returncode: SKIPPED_NO_PAYLOAD_ROWS
signals_found_count: 0
open_order_intent_count: 0
close_intent_count: 0
order_intents_read: 0
order_previews_created: 0
payload_rows_out: 0
mt5_order_send_called_count: 0
mt5_sent_rows: 0
```

Decision:

```text
One-cycle integrated dry-run no-signal path: PASS
safe_no_send: PASS
Existing Mochipoyo BAT unchanged: PASS
Real order send: NOT CALLED
```

### Aligned loop wrapper

Script:

```text
scripts/run_gold_multi_strategy_demo_dry_run_loop_aligned.py
```

Validated command:

```cmd
python scripts\run_gold_multi_strategy_demo_dry_run_loop_aligned.py --csv-dir "<MT5_FILES_DIR>" --iterations 2 --interval-seconds 0
```

Validated result:

```text
loop lock: acquired
cycle 1: cycle_ok true / safe_no_send true
cycle 2: cycle_ok true / safe_no_send true
loop lock: released
signals_found_count: 0
open_order_intent_count: 0
close_intent_count: 0
payload_rows_out: 0
mt5_dry_run: SKIPPED_NO_PAYLOAD_ROWS
mt5_order_send_called_count: 0
mt5_sent_rows: 0
```

Decision:

```text
multi-strategy demo dry-run aligned loop: PASS
2-cycle finite loop: PASS
lock acquire/release: PASS
no-signal/no-payload path: PASS
safe_no_send: PASS
Existing Mochipoyo BAT unchanged: PASS
Real order send: NOT CALLED
```

## Non-goals for the next integration step

Do not do these yet:

```text
Do not modify scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat.
Do not modify scripts/run_mochipoyo_gold_minimal_live_loop_aligned.py.
Do not write to existing Mochipoyo notification ledgers.
Do not write to existing Mochipoyo trigger-state CSVs.
Do not write to existing demo autotrade order ledger.
Do not send Discord messages.
Do not pass --send to send_mt5_order_from_payload.py.
Do not create live close orders.
```

## Implemented one-cycle runner

Script:

```text
scripts/run_gold_multi_strategy_demo_dry_run_cycle.py
```

Purpose:

Run one full multi-strategy dry-run cycle:

```text
1. Run multi-strategy router
2. Run autotrade adapter dry-run
3. Run Mochipoyo-compatible order payload bridge dry-run
4. Run send_mt5_order_from_payload.py WITHOUT --send
5. Write one combined cycle result
6. Append one combined cycle log row
```

Default output directory:

```text
data/research_results/gold_multi_strategy_demo_dry_run_cycle
```

Strategy-specific output directories:

```text
data/research_results/gold_c_env_rr2_72h_live_scan
data/research_results/gold_h1h4_bear_ab_live_loop
```

Router output directory:

```text
data/research_results/gold_multi_strategy_dry_run
```

Adapter output directory:

```text
data/research_results/gold_multi_strategy_autotrade_adapter_dry_run
```

Payload bridge output directory:

```text
data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run
```

MT5 dry-run output directory:

```text
data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/mt5_order_check_dry_run
```

## Implemented aligned loop wrapper

Script:

```text
scripts/run_gold_multi_strategy_demo_dry_run_loop_aligned.py
```

Purpose:

Run the new cycle runner repeatedly on an aligned schedule.

Recommended default cadence:

```text
align_to_second: 2
```

Because existing MT5 CSV export writes around second 00, this matches the existing Mochipoyo aligned-loop idea while remaining isolated.

Lock file:

```text
<data out dir>/gold_multi_strategy_demo_dry_run_loop.lock
```

Validated status:

```text
PASS
```

## Proposed BAT file

Recommended BAT:

```text
scripts/run_gold_multi_strategy_demo_dry_run_aligned.bat
```

Important:

This must be a new BAT file. Do not modify:

```text
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
```

Recommended BAT behavior:

```text
- use XMTrading demo login 75539039
- use broker symbol GOLD#
- use fixed lot 0.01
- use magic 26050601 or a new multi-strategy magic number after review
- use position policy block_any
- use max symbol positions 1
- use max symbol lot 0.01
- never pass --send
- never send Discord
- stop on cycle errors unless explicitly disabled
```

## One-cycle runner arguments

Core arguments:

```text
--csv-dir <MT5_FILES_DIR>
--out-dir data\research_results\gold_multi_strategy_demo_dry_run_cycle
--router-out-dir data\research_results\gold_multi_strategy_dry_run
--buy-out-dir data\research_results\gold_c_env_rr2_72h_live_scan
--sell-out-dir data\research_results\gold_h1h4_bear_ab_live_loop
--adapter-out-dir data\research_results\gold_multi_strategy_autotrade_adapter_dry_run
--payload-out-dir data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run
--mt5-dry-run-out-dir data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\mt5_order_check_dry_run
--broker-symbol GOLD#
--fixed-lot 0.01
--magic 26050601
--expected-login 75539039
--require-demo-account
--position-policy block_any
--max-symbol-positions 1
--max-symbol-lot 0.01
--select-symbol
```

Do not include:

```text
--send
--discord-send
--commit-ledger
--commit-trigger-state
```

## Combined cycle output files

Outputs:

```text
latest_multi_strategy_demo_dry_run_cycle_result.json
multi_strategy_demo_dry_run_cycle_log.csv
```

Cycle summary fields:

```text
cycle_start_utc
cycle_end_utc
cycle_ok
router_returncode
adapter_returncode
payload_bridge_returncode
mt5_dry_run_returncode
router_ok
adapter_ok
bridge_ok
order_intents_read
close_intents_read
order_previews_created
close_previews_created
payload_rows_out
valid_order_payloads
mt5_rows_out
mt5_dry_run_check_ok_rows
mt5_blocked_position_policy_rows
mt5_order_send_called_count
mt5_sent_rows
mt5_error_rows
safe_no_send
```

`safe_no_send` must be true only if:

```text
mt5_order_send_called_count == 0
mt5_sent_rows == 0
```

## Handling no-signal cycles

If router produces no order intents and no close intents:

```text
router_ok: true
adapter_ok: true
bridge_ok: true
payload_rows_out: 0
mt5 stage: skipped or rows_out 0
cycle_ok: true
safe_no_send: true
```

No-signal cycles are not errors.

## Handling existing-position block_any cycles

If payload rows exist but a GOLD# position is already open:

```text
mt5_order_send_called_count: 0
mt5_sent_rows: 0
mt5_blocked_position_policy_rows: 1
mt5_error_rows: 1
safe_no_send: true
cycle_ok: true, if and only if blocked policy is explicitly allowed as safe
```

The one-cycle runner normalizes this as a safe block, not a fatal error, when `--treat-position-block-as-safe` is true.

Default:

```text
--treat-position-block-as-safe enabled
```

Reason:

The existing demo BAT already uses `block_any`, so an existing position should safely block the new candidate rather than fail the whole loop.

## Close intent limitation

Current `send_mt5_order_from_payload.py` only opens market orders from `order_payloads.csv`.

It does not currently execute close intents.

Therefore, in the first integrated dry-run cycle:

```text
adapter_close_preview.csv can be generated
combined close intent can be logged
but no MT5 close action is executed
```

Close intent execution should be a separate future design:

```text
scripts/send_mt5_close_from_payload.py  # future, not yet implemented
```

Before implementing close execution, confirm:

```text
position ticket selection rules
strategy_id/signal_key matching
partial close vs full close
BUY close_side SELL / SELL close_side BUY mapping
duplicate close ledger
market-close/data-gap TIME_EXIT handling
```

## Recommended validation sequence

### Step 1: One-cycle dry-run runner

Implemented and validated:

```text
scripts/run_gold_multi_strategy_demo_dry_run_cycle.py
```

Status:

```text
PASS
```

### Step 2: Aligned loop wrapper

Implemented and validated:

```text
scripts/run_gold_multi_strategy_demo_dry_run_loop_aligned.py
```

Status:

```text
PASS
```

### Step 3: Create new BAT

Implement:

```text
scripts/run_gold_multi_strategy_demo_dry_run_aligned.bat
```

The BAT should call the new aligned loop wrapper only.

It must not call the existing Mochipoyo aligned loop.

### Step 4: Later send-mode design

Only after extended dry-run validation should send mode be designed.

Before send mode:

```text
backup branch or file snapshot required
explicit user approval required
expected login required
require demo account required
position policy block_any required
max orders 1 required
max symbol lot 0.01 required
manual confirmation that no unwanted position is open
```

## Current recommendation

Proceed with Step 3 only:

```text
Implement scripts/run_gold_multi_strategy_demo_dry_run_aligned.bat
```

Do not implement send mode.
Do not modify the existing Mochipoyo BAT.
Do not implement close execution yet.

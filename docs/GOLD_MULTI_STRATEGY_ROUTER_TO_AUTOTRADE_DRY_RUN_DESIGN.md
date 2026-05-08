# GOLD multi-strategy router to autotrade dry-run design

Last updated: 2026-05-08

## Purpose

This document defines the next integration step after isolated BUY/SELL strategy dry-runs and the multi-strategy dry-run router.

The goal is to prepare a safe bridge from:

```text
strategy-specific isolated dry-run outputs
  ↓
scripts/run_gold_multi_strategy_dry_run_cycle.py
  ↓
router-level combined intents
```

toward the existing Mochipoyo/demo/autotrade flow, without directly connecting to real order placement yet.

## Current status

### BUY side

Strategy:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

Status:

```text
isolated dry-run: PASS
no-signal/no-position path: PASS
existing Mochipoyo/demo/autotrade: NOT CONNECTED
```

### SELL side

Strategy family:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

Status:

```text
isolated dry-run: PASS
TP path: PASS
SL path: PASS
TIME_EXIT close intent path: PASS
duplicate signal_key path: PASS
resolved position ledger path: PASS
duplicate order intent safety path: PASS
2-cycle loop path: PASS
existing Mochipoyo/demo/autotrade: NOT CONNECTED
```

### Multi-strategy router

Script:

```text
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

Validated outputs:

```text
latest_multi_strategy_cycle_result.json
multi_strategy_cycle_log.csv
strategy_status_latest.csv
combined_order_intent_dry_run.jsonl
combined_close_intent_dry_run.jsonl
```

Validated paths:

```text
BUY/SELL no-signal aggregation: PASS
strategy status aggregation: PASS
order intent aggregation: PASS
close intent aggregation: PASS
aggregate-only mode: PASS
```

## Non-goals for the next step

Do not do these yet:

```text
Do not modify run_mochipoyo_gold_demo_autotrade_forever_aligned.bat.
Do not write to existing Mochipoyo live ledgers.
Do not write to existing demo autotrade order-intent files.
Do not send Discord messages.
Do not place MT5 orders.
Do not create live close orders.
```

The next step is only a dry-run adapter layer.

## Proposed next script

Recommended script name:

```text
scripts/run_gold_multi_strategy_autotrade_adapter_dry_run.py
```

Purpose:

```text
Read router-level combined intents.
Validate schema and safety fields.
Normalize BUY/SELL order intents into one adapter preview schema.
Normalize close intents into one adapter close preview schema.
Write adapter-only dry-run outputs.
Do not call MT5.
Do not call existing Mochipoyo autotrade code.
```

Recommended output directory:

```text
data/research_results/gold_multi_strategy_autotrade_adapter_dry_run/
```

## Adapter inputs

Primary router output directory:

```text
data/research_results/gold_multi_strategy_dry_run/
```

Required input files:

```text
combined_order_intent_dry_run.jsonl
combined_close_intent_dry_run.jsonl
strategy_status_latest.csv
latest_multi_strategy_cycle_result.json
```

The adapter should also support explicitly passing an alternate router directory:

```cmd
--router-out-dir data\research_results\gold_multi_strategy_dry_run_aggregate_only_time_exit
```

This is useful for controlled aggregate-only validation.

## Adapter output files

Recommended files:

```text
latest_adapter_result.json
adapter_cycle_log.csv
adapter_order_preview.csv
adapter_order_preview.jsonl
adapter_close_preview.csv
adapter_close_preview.jsonl
adapter_rejects.csv
```

## Order intent handling

Input intent types:

```text
OPEN_POSITION
OBSERVE_ONLY
DUPLICATE_SKIP
```

Adapter behavior:

```text
OPEN_POSITION:
  validate and include in adapter_order_preview

OBSERVE_ONLY:
  do not create an executable order preview
  log as observe-only or skip reason

DUPLICATE_SKIP:
  do not create an executable order preview
  log as duplicate skip
```

Required checks for OPEN_POSITION:

```text
dry_run == true
symbol == GOLD or expected broker symbol mapping target
strategy_id is non-empty
condition_id is non-empty
signal_key is non-empty
intent_type == OPEN_POSITION
direction in {BUY, SELL}
entry_price_reference is finite
sl_price is finite
tp_price is finite
risk_price > 0
rr > 0
lot.effective_lot > 0
```

Direction-specific price sanity checks:

```text
BUY:
  sl_price < entry_price_reference
  tp_price > entry_price_reference

SELL:
  sl_price > entry_price_reference
  tp_price < entry_price_reference
```

The adapter preview should include:

```text
adapter_action = WOULD_OPEN_POSITION_DRY_RUN
side = BUY or SELL
symbol
strategy_id
condition_id
signal_key
rank
entry_type
entry_price_reference
sl_price
tp_price
risk_price
reward_price
rr
max_hold_hours
base_lot
lot_multiplier
effective_lot
router_strategy_slot
router_source_path
```

## Close intent handling

Input close intent type:

```text
CLOSE_POSITION
```

Adapter behavior:

```text
CLOSE_POSITION:
  validate and include in adapter_close_preview
```

Required checks:

```text
dry_run == true
intent_type == CLOSE_POSITION
symbol is non-empty
strategy_id is non-empty
condition_id is non-empty
signal_key is non-empty
close_key is non-empty
direction in {BUY, SELL}
close_side in {BUY, SELL}
entry_price_reference is finite
exit_price_reference is finite
realized_r_reference is finite
```

Direction-specific close-side check:

```text
source direction BUY  => close_side SELL
source direction SELL => close_side BUY
```

The adapter close preview should include:

```text
adapter_action = WOULD_CLOSE_POSITION_DRY_RUN
symbol
strategy_id
condition_id
signal_key
close_key
direction
close_side
close_reason
entry_time
entry_price_reference
exit_time_reference
exit_price_reference
realized_r_reference
lot_weighted_r_reference
effective_lot
router_strategy_slot
router_source_path
```

## Reject handling

Any intent that fails validation should be written to:

```text
adapter_rejects.csv
```

Recommended reject fields:

```text
reject_time_utc
intent_kind
intent_type
strategy_id
condition_id
signal_key
router_strategy_slot
router_source_path
reject_reason
raw_json
```

The adapter should not fail the whole run for one rejected intent unless `--strict` is provided.

Recommended options:

```text
--strict
  return non-zero if any reject exists

--allow-symbol GOLD
  default allowed symbol

--broker-symbol GOLD# or XAUUSD
  optional mapping target, but do not place order yet
```

## Duplicate handling at adapter level

The adapter should keep its own preview ledger to avoid repeatedly emitting the same adapter preview.

Recommended file:

```text
adapter_preview_ledger.csv
```

For open previews, dedupe by:

```text
open_preview_key = strategy_id | signal_key | OPEN_POSITION
```

For close previews, dedupe by:

```text
close_preview_key = strategy_id | close_key | CLOSE_POSITION
```

If already seen:

```text
adapter_action = DUPLICATE_PREVIEW_SKIP
```

and do not write a second executable preview row.

## Recommended validation order

### Step 1: Adapter aggregate-only TIME_EXIT test

Use the router aggregate-only output that already contains one SELL OPEN_POSITION and one SELL CLOSE_POSITION.

Input router directory:

```text
data/research_results/gold_multi_strategy_dry_run_aggregate_only_time_exit
```

Expected adapter result:

```text
router_ok: true
order_intents_read: 1
close_intents_read: 1
order_previews_created: 1
close_previews_created: 1
rejects: 0
```

### Step 2: Adapter duplicate preview test

Run the same adapter command twice with the same adapter out directory.

Expected second run:

```text
order_previews_created: 0
close_previews_created: 0
duplicate_previews_skipped: 2
rejects: 0
```

### Step 3: Adapter normal router no-signal test

Input router directory:

```text
data/research_results/gold_multi_strategy_dry_run
```

Expected:

```text
order_intents_read: 0
close_intents_read: 0
order_previews_created: 0
close_previews_created: 0
rejects: 0
```

## Later connection to existing demo autotrade

Only after the adapter passes should actual connection design begin.

Potential final flow:

```text
run_gold_multi_strategy_dry_run_cycle.py
  ↓
run_gold_multi_strategy_autotrade_adapter_dry_run.py
  ↓
future broker-specific demo order-intent writer
  ↓
existing demo autotrade execution layer
```

Before writing into existing demo autotrade inputs, confirm:

```text
1. Existing order-intent schema expected by demo autotrade.
2. Existing symbol mapping, e.g. GOLD# / XAUUSD.
3. Existing lot sizing and max lot rules.
4. Existing account safety limits.
5. Existing open-position duplicate checks.
6. Existing close-position duplicate checks.
7. Whether existing flow supports strategy_id and signal_key.
8. Whether existing flow supports both BUY and SELL in the same queue.
9. Whether existing flow supports TIME_EXIT close intents.
10. Backup branch / file snapshot before any mutation.
```

## Current recommendation

Implement the adapter as a separate dry-run script next.

Do not connect the router directly to existing Mochipoyo/demo autotrade yet.

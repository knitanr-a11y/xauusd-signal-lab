# GOLD multi-strategy signal to Mochipoyo flow map

Last updated: 2026-05-10

## Purpose

This document maps the actual implemented file path from the GOLD BUY/SELL strategy signals to the Mochipoyo-compatible payload and guarded sender layer.

This is Phase 1 of the final roadmap: confirm where `BUY_C_ENV_RR2_72H` and `SELL_H1H4_BEAR_AB` are generated, routed, converted to payload, and passed toward the sender.

## High-level implemented chain

```text
MT5 / MQL5 CSV files
  ↓
BUY isolated live scan / position monitor
SELL isolated live scan / position monitor
  ↓
GOLD multi-strategy dry-run router
  ↓
combined order / close intent JSONL
  ↓
autotrade adapter dry-run preview
  ↓
Mochipoyo-compatible order_payloads.csv bridge
  ↓
send_mt5_order_from_payload.py dry-run / guarded send
  ↓
sender-native registry preview / policy preview support layer
```

## Strategy slots

### BUY

```text
strategy_slot: BUY_C_ENV_RR2_72H
strategy_id / condition_id: GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

### SELL

```text
strategy_slot: SELL_H1H4_BEAR_AB
strategy_id / family: GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

SELL rank behavior:

```text
CORE_AB_CONFIRM -> trade_enabled=true
B_ONLY_SAFE     -> trade_enabled=true
A_ONLY_OBSERVE  -> trade_enabled=false
```

## Actual file map

### 1. BUY signal scan once

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
```

Role:

```text
Reads GOLD CSVs.
Builds H4/H1/M15 context.
Checks latest confirmed M15.
When eligible, writes order_intent_dry_run.json.
```

Key outputs:

```text
latest_scan_result.json
latest_signal_payload.json
order_intent_dry_run.json
notification_preview_latest.txt
live_scan_log.csv
signal_ledger.csv
```

### 2. BUY isolated dry-run cycle

```text
scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
```

Role:

```text
Runs BUY live scan once.
Runs BUY position monitor once.
Keeps BUY outside existing Mochipoyo flow.
```

Calls:

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
scripts/run_gold_c_env_rr2_72h_position_monitor_once.py
```

### 3. SELL signal scan once

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
```

Role:

```text
Reads GOLD CSVs.
Builds D1/H4/H1/M15 context.
Checks latest confirmed M15 for bearish A/B classifier state.
Writes OPEN_POSITION / OBSERVE_ONLY / DUPLICATE_SKIP intent.
```

Key outputs:

```text
latest_scan_result.json
latest_signal_payload.json
order_intent_dry_run.json
notification_preview_latest.txt
latest_raw_candidates.csv
latest_live_flag_candidates.csv
live_scan_log.csv
signal_ledger.csv
```

### 4. SELL isolated dry-run loop

```text
scripts/run_gold_h1h4_bear_ab_dry_run_loop.py
```

Role:

```text
Runs SELL live scan.
Runs SELL position monitor.
Can run once, repeated, or M15-aligned.
Keeps SELL outside existing Mochipoyo flow.
```

Calls:

```text
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
scripts/run_gold_h1h4_bear_ab_position_monitor_once.py
```

### 5. Multi-strategy router

```text
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

Role:

```text
Runs or aggregates both isolated strategy dry-run cycles.
Normalizes BUY/SELL strategy status.
Reads each strategy order_intent_dry_run.json and close_intent_dry_run.json.
Adds router_strategy_slot / router_strategy_id / router_source_path.
Writes router-level combined intent files.
```

Calls:

```text
BUY:  scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
SELL: scripts/run_gold_h1h4_bear_ab_dry_run_loop.py
```

Key outputs:

```text
latest_multi_strategy_cycle_result.json
multi_strategy_cycle_log.csv
strategy_status_latest.csv
combined_order_intent_dry_run.jsonl
combined_close_intent_dry_run.jsonl
```

This is the point where BUY and SELL become one combined multi-strategy flow.

### 6. Autotrade adapter dry-run

```text
scripts/run_gold_multi_strategy_autotrade_adapter_dry_run.py
```

Role:

```text
Reads combined_order_intent_dry_run.jsonl / combined_close_intent_dry_run.jsonl.
Converts OPEN_POSITION intents into adapter_order_preview.csv.
Converts CLOSE_POSITION intents into adapter_close_preview.csv.
Rejects malformed rows.
Maintains adapter_preview_ledger.csv for duplicate preview skipping.
```

Key outputs:

```text
latest_adapter_result.json
adapter_order_preview.csv
adapter_order_preview.jsonl
adapter_close_preview.csv
adapter_close_preview.jsonl
adapter_rejects.csv
adapter_preview_ledger.csv
```

Important retained fields:

```text
strategy_id
condition_id
signal_key
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
router_strategy_id
router_source_path
```

### 7. Mochipoyo-compatible payload bridge

```text
scripts/build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py
```

Role:

```text
Reads adapter_order_preview.csv.
Builds order_payloads.csv compatible with send_mt5_order_from_payload.py.
Still dry-run bridge only.
```

Key outputs:

```text
order_payloads.csv
order_payloads.json
payload_bridge_rejects.csv
```

Important output columns:

```text
symbol
broker_symbol
direction
lot
entry_price_reference
sl_price
tp_price
rr
magic_number
comment
payload_key
order_key
pair_name
candidate_rank
candidate_name
signal_close_time
entry_time
strategy_id
condition_id
signal_key
router_strategy_slot
router_strategy_id
router_source_path
adapter_preview_key
```

Current limitation:

```text
Default lot is fixed_lot=0.01.
Adapter effective_lot is used only with --use-adapter-lot.
```

### 8. Demo autotrade send cycle runner

```text
scripts/run_gold_multi_strategy_demo_autotrade_send_cycle.py
```

Role:

```text
Runs router → adapter → payload bridge → send_mt5_order_from_payload.py → summary/log.
```

Important safety behavior:

```text
Refuses to pass --send unless --enable-demo-send is explicitly provided.
Defaults to broker_symbol=GOLD#.
Defaults to fixed_lot=0.01.
Defaults to position_policy=block_any.
Does not modify existing Mochipoyo BAT files.
Does not write existing Mochipoyo notification ledgers or trigger-state CSVs.
Does not execute close intents.
```

Important limitation:

```text
It does not yet use block_same_strategy_and_opposite_direction as the active send policy.
It only uses existing sender policies: block_any / allow_same_direction / allow_any_until_max.
```

### 9. Sender / registry preview support

```text
scripts/send_mt5_order_from_payload.py
```

Role:

```text
Reads order_payloads.csv.
Validates payload.
Checks MT5 account/symbol/position policy.
Calls mt5.order_check.
Calls mt5.order_send only with explicit --send.
Can emit disabled-by-default registry preview CSV/JSON when preview flags are explicitly passed.
```

Preview flags:

```text
--registry-preview-out-csv
--registry-preview-out-json
--registry-preview-include-dry-run-check-ok
--registry-preview-include-sent
```

## Current conclusion

The signal-to-payload path exists:

```text
BUY scan / SELL scan
→ multi-strategy router
→ adapter preview
→ Mochipoyo-compatible order_payloads.csv
→ guarded sender dry-run / optional guarded send
```

The sender/registry safety bridge exists:

```text
send_mt5_order_from_payload.py
→ optional registry preview
→ mock positions / reconcile / policy preview
```

The missing clean bridge is an independent dry-run wrapper that ties both halves together without requiring `--enable-demo-send` and without touching the existing Mochipoyo production loop.

## Main gaps before true Mochipoyo loop integration

```text
1. Need routine validation of router → adapter → payload → sender dry-run on current MT5 CSVs.
2. Default lot remains fixed at 0.01; strategy effective_lot is not active unless --use-adapter-lot is chosen.
3. Active demo send runner still defaults to block_any, not registry-aware block_same_strategy_and_opposite_direction.
4. Close intents are generated/previewed but not MT5-executed.
5. Existing Mochipoyo loop remains separate and intentionally untouched.
```

## Recommended next step

Create or confirm an independent GOLD multi-strategy Mochipoyo-loop dry-run wrapper that:

```text
1. runs router
2. runs adapter
3. builds order_payloads.csv
4. calls send_mt5_order_from_payload.py WITHOUT --send
5. optionally calls sender-native registry preview flags
6. writes one summary JSON
7. never touches existing Mochipoyo production BAT / ledgers / trigger-state
```

This is the correct next bridge between the signal work and future Mochipoyo loop integration.

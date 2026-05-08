# GOLD multi-strategy registry-from-payload preview validation

Last updated: 2026-05-09

## Purpose

This document records validation results for building preview `position_registry.csv` rows from order payloads plus synthetic send-result metadata.

The goal is to verify the exact registry row shape that the real sender should write only after a confirmed successful `order_send`, without modifying the real sender yet.

## Safety boundary

The preview builder is file-only and non-executing.

```text
No MetaTrader5 import.
No mt5.order_check.
No mt5.order_send.
No existing Mochipoyo ledger mutation.
No trigger-state mutation.
No production registry mutation by default.
```

The real sender remains unchanged.

```text
scripts/send_mt5_order_from_payload.py: not modified
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat: not modified
existing Mochipoyo ledger files: not modified
existing trigger-state files: not modified
```

## Implemented script

```text
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
```

Commit:

```text
0090bad31e0b4e0a3bc9b31e90c3df2a7d6269e6
```

Purpose:

```text
order_payloads.csv row
+ synthetic successful send result fields
  - position_ticket
  - order_ticket
  - deal_ticket
  - account_login
  - account_server
=> preview/test position_registry.csv row
```

Primary outputs:

```text
data/research_results/gold_multi_strategy_position_registry/position_registry_from_payload_preview.csv
data/research_results/gold_multi_strategy_position_registry/position_registry_from_payload_preview.json
```

## Validation input

Payload input:

```text
data/research_results/gold_multi_strategy_position_policy_preflight/order_payloads_policy_test_same_direction_buy.csv
```

Synthetic send result fields:

```text
account_login=75539039
account_server=XMTrading-MT5 3
position_ticket_start=990001
order_ticket_start=880001
deal_ticket_start=770001
position_status=ACTIVE
```

Command:

```cmd
python scripts\build_gold_multi_strategy_position_registry_from_payload_preview.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --out-dir data\research_results\gold_multi_strategy_position_registry --output-csv data\research_results\gold_multi_strategy_position_registry\position_registry_from_payload_preview.csv --account-login 75539039 --account-server "XMTrading-MT5 3" --position-ticket-start 990001 --order-ticket-start 880001 --deal-ticket-start 770001 --position-status ACTIVE
```

Observed summary:

```text
preview_ok: true
reason: REGISTRY_PREVIEW_ROWS_BUILT
rows_in: 1
rows_out_new: 1
rows_out_total: 1
validation_error_rows: 0
```

Observed registry row:

```text
position_ticket=990001
broker_symbol=GOLD#
direction=BUY
lot=0.01
strategy_key=BUY_C_ENV_RR2_72H
strategy_alias=BUY_C
position_status=ACTIVE
signal_key=POLICY_TEST|same_direction_buy|BUY|0.01|BUY_C_ENV_RR2_72H
```

Safety output:

```text
mt5_imported: false
order_check_called: false
order_send_called: false
existing_mochipoyo_ledger_mutated: false
trigger_state_mutated: false
production_registry_mutated_by_default: false
```

Decision:

```text
PASS.
```

## Reconciliation validation

After generating the preview registry row, it was reconciled against the matching mock position:

Mock positions input:

```text
data/research_results/gold_multi_strategy_position_policy_preflight/mock_positions_same_strategy_buy_c.csv
```

Command:

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_from_payload_preview.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD#
```

Observed summary:

```text
reconcile_ok: true
registry_status: REGISTRY_READ_OK
registry_rows: 1
active_registry_rows: 1
positions_rows: 1
reconcile_rows: 1
matched_active_registry_rows: 1
matched_with_mismatch_rows: 0
missing_position_rows: 0
unregistered_position_rows: 0
status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Observed reconciliation row:

```text
row_type=ACTIVE_REGISTRY_ROW
registry_position_ticket=990001
registry_strategy_key=BUY_C_ENV_RR2_72H
position_ticket=990001
position_symbol=GOLD#
position_direction=BUY
position_lot=0.01
ticket_match=true
symbol_match=true
direction_match=true
lot_match=true
strategy_detected_in_position=true
reconcile_status=REGISTRY_ACTIVE_MATCHED
reconcile_reason=active registry row matched current open position
```

Safety output:

```text
order_check_called_count: 0
order_send_called_count: 0
registry_mutated: false
ledger_mutated: false
trigger_state_mutated: false
```

Decision:

```text
PASS.
```

## End-to-end policy preview validation

After generating and reconciling the preview registry row, the registry-aware policy preview was run using the generated registry row.

Command:

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_from_payload_preview.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD# --max-total-positions 5 --max-lot-per-order 0.02
```

Observed summary:

```text
preview_ok: true
reason: POLICY_PREVIEW_EVALUATED
rows_in: 1
rows_out: 1
allow_rows: 0
blocked_rows: 1
same_strategy_blocked_rows: 1
opposite_direction_blocked_rows: 0
total_position_cap_blocked_rows: 0
per_order_lot_blocked_rows: 0
duplicate_key_blocked_rows: 0
registry_inconsistency_blocked_rows: 0
reconcile_status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Observed row:

```text
requested_strategy_key=BUY_C_ENV_RR2_72H
requested_symbol=GOLD#
requested_direction=BUY
requested_lot=0.01
existing_total_positions=1
existing_symbol_positions=1
existing_symbol_directions=BUY
registry_matched_rows=1
registry_missing_position_rows=0
unregistered_position_rows=0
same_strategy_blocked=true
opposite_direction_blocked=false
total_position_cap_blocked=false
per_order_lot_blocked=false
duplicate_key_blocked=false
registry_inconsistency_blocked=false
final_policy_decision=BLOCK
```

Final policy reason:

```text
same_strategy: ACTIVE matched registry position already exists for strategy=BUY_C_ENV_RR2_72H; tickets=['990001']
```

Safety output:

```text
mt5_imported: false
order_check_called_count: 0
order_send_called_count: 0
registry_mutated: false
ledger_mutated: false
trigger_state_mutated: false
```

Decision:

```text
PASS.
```

## Validation matrix

Current registry-from-payload preview state:

```text
Payload row converted to registry preview row: PASS
Synthetic ticket/order/deal metadata stored: PASS
strategy_key and strategy_alias inferred correctly: PASS
Preview registry row reconciles with matching mock position: PASS
Generated registry row feeds registry-aware policy preview: PASS
same_strategy BLOCK from generated registry row: PASS
Read-only safety counters: PASS
```

## End-to-end validated chain

The following chain is now validated without touching the real sender:

```text
controlled payload
→ synthetic successful send result
→ preview position_registry row
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

## Design implication

This confirms the basic write-shape needed after a future successful send:

```text
payload metadata
+ confirmed MT5 tickets/order/deal data
+ account identity
+ strategy ownership fields
=> ACTIVE position_registry row
```

The preview row can already be consumed by:

```text
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
scripts/run_gold_multi_strategy_registry_policy_preview.py
```

## Current recommendation

Do not modify the real sender yet.

Next safe step:

```text
Design sender-adjacent dry-run integration for registry row creation after simulated successful send.
```

The next layer should still be dry-run only and should not call `order_send`.

Potential next script:

```text
scripts/run_gold_multi_strategy_demo_send_registry_preview_cycle.py
```

Purpose:

```text
Take current payload output from the guarded demo send chain,
simulate a successful send result,
build a preview registry row,
run reconciliation,
run registry-aware policy preview,
and write a single summary JSON/CSV.
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

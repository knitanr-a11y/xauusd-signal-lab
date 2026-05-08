# GOLD multi-strategy demo send registry preview cycle validation

Last updated: 2026-05-09

## Purpose

This document records validation results for the sender-adjacent registry preview cycle.

The cycle validates the following chain in one command:

```text
payload
→ synthetic send result
→ preview position_registry row
→ registry reconciliation
→ registry-aware policy preview
→ summary JSON/CSV
```

This is still a dry-run / preview-only integration layer.

The real MT5 sender remains unchanged.

```text
scripts/send_mt5_order_from_payload.py: not modified
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat: not modified
existing Mochipoyo ledger files: not modified
existing trigger-state files: not modified
```

## Safety boundary

The cycle must not execute or mutate live trading state.

Validated safety output:

```text
mt5_imported: false
order_check_called_count: 0
order_send_called_count: 0
registry_mutated: false
ledger_mutated: false
trigger_state_mutated: false
real_sender_modified: false
existing_bat_modified: false
```

## Implemented script

```text
scripts/run_gold_multi_strategy_demo_send_registry_preview_cycle.py
```

Commit:

```text
ed23cf40949e79fe6deab0f1742a854ef58cc66d
```

Primary outputs:

```text
data/research_results/gold_multi_strategy_demo_send_registry_preview_cycle/demo_send_registry_preview_cycle_summary.json
data/research_results/gold_multi_strategy_demo_send_registry_preview_cycle/demo_send_registry_preview_cycle_summary.csv
data/research_results/gold_multi_strategy_demo_send_registry_preview_cycle/position_registry_from_payload_preview_cycle.csv
data/research_results/gold_multi_strategy_demo_send_registry_preview_cycle/position_registry_reconcile_cycle.csv
data/research_results/gold_multi_strategy_demo_send_registry_preview_cycle/registry_policy_preview_cycle.csv
```

## Validation command

```cmd
python scripts\run_gold_multi_strategy_demo_send_registry_preview_cycle.py --payload-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_demo_send_registry_preview_cycle --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --account-login 75539039 --account-server "XMTrading-MT5 3" --position-ticket-start 990001 --order-ticket-start 880001 --deal-ticket-start 770001 --position-status ACTIVE
```

## Input payload

```text
payload_csv=data/research_results/gold_multi_strategy_position_policy_preflight/order_payloads_policy_test_same_direction_buy.csv
payload_rows=1
symbol=GOLD#
max_orders=1
```

Payload strategy:

```text
requested_strategy_key=BUY_C_ENV_RR2_72H
requested_symbol=GOLD#
requested_direction=BUY
requested_lot=0.01
```

## Synthetic send result

```text
account_login=75539039
account_server=XMTrading-MT5 3
position_ticket=990001
order_ticket=880001
deal_ticket=770001
position_status=ACTIVE
```

## Cycle summary

Observed:

```text
cycle_ok: true
reason: CYCLE_EVALUATED
payload_rows: 1
```

Child steps:

```text
build_registry_from_payload_preview: PASS, returncode=0
registry_reconcile_dry_run: PASS, returncode=0
registry_policy_preview: PASS, returncode=0
```

Decision:

```text
PASS.
```

## Step 1: registry builder result

Observed:

```text
preview_ok: true
reason: REGISTRY_PREVIEW_ROWS_BUILT
rows_in: 1
rows_out_new: 1
rows_out_total: 1
validation_error_rows: 0
```

Generated registry row:

```text
account_login=75539039
account_server=XMTrading-MT5 3
position_ticket=990001
order_ticket=880001
deal_ticket=770001
broker_symbol=GOLD#
symbol=GOLD
direction=BUY
lot=0.01
entry_price=4727.67
sl_price=4717.67
tp_price=4747.67
strategy_key=BUY_C_ENV_RR2_72H
strategy_alias=BUY_C
strategy_id=GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
position_status=ACTIVE
sender_report_json=SYNTHETIC_SEND_RESULT_FROM_DEMO_SEND_REGISTRY_PREVIEW_CYCLE
```

Decision:

```text
PASS.
```

## Step 2: registry reconciliation result

Observed:

```text
reconcile_ok: true
reason: RECONCILE_EVALUATED
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

Matched row:

```text
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
```

Decision:

```text
PASS.
```

## Step 3: registry policy preview result

Observed:

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

Final policy decision:

```text
final_policy_decision=BLOCK
```

Final policy reason:

```text
same_strategy: ACTIVE matched registry position already exists for strategy=BUY_C_ENV_RR2_72H; tickets=['990001']
```

Decision:

```text
PASS.
```

## Validation matrix

Current demo send registry preview cycle state:

```text
payload detected: PASS
registry preview row generated from payload + synthetic send result: PASS
registry preview row reconciles with mock position: PASS
registry-aware policy preview consumes generated registry: PASS
same_strategy BLOCK from generated registry row: PASS
summary JSON/CSV generated: PASS
all child steps returncode 0: PASS
read-only safety counters: PASS
```

## End-to-end validated chain

The following chain is validated in one command:

```text
controlled payload
→ synthetic successful send result
→ preview registry row
→ registry reconcile
→ registry policy preview
→ same_strategy BLOCK
→ combined summary JSON/CSV
```

## Design implications

This script is a safe rehearsal for the future sender-adjacent registry flow.

It confirms that after a real successful demo send, the system can conceptually:

```text
1. extract payload metadata
2. combine it with confirmed MT5 ticket/order/deal data
3. create an ACTIVE registry row
4. reconcile registry ownership with current MT5 positions
5. block duplicate same-strategy entries through registry-aware policy
```

## Current recommendation

Do not modify the real sender yet.

Next safe step:

```text
Design a sender-adjacent dry-run wrapper that reads an actual guarded demo send dry-run report, not synthetic fixed tickets, and maps its result into the registry preview builder.
```

This should still not call `order_send` and should still not write the production registry.

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

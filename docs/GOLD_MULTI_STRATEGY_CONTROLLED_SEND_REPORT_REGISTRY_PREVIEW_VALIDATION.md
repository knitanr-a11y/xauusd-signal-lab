# GOLD multi-strategy controlled send-report registry preview validation

Last updated: 2026-05-10

## Purpose

This document records validation results for the controlled payload-bearing send-report path.

The goal is to validate the path that was not reachable from the latest real guarded demo send report because that report had no payload rows.

Validated path:

```text
controlled payload-bearing guarded-send-style report
→ payload CSV extraction
→ registry preview row generation
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

This remains dry-run / preview-only.

## Safety boundary

No live trading operation was performed.

```text
No MetaTrader5 import.
No mt5.order_check.
No mt5.order_send.
No real sender modification.
No existing BAT modification.
No existing Mochipoyo ledger mutation.
No trigger-state mutation.
No production registry mutation.
```

The real sender remains unchanged.

```text
scripts/send_mt5_order_from_payload.py: not modified
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat: not modified
existing Mochipoyo ledger files: not modified
existing trigger-state files: not modified
```

## Implemented builder

```text
scripts/build_gold_multi_strategy_controlled_send_report.py
```

Commit:

```text
c13a9dd8daf15a46164e7e117929d206996af0df
```

Purpose:

```text
controlled payload CSV
→ payload_bridge_send_controlled/order_payloads.csv
→ latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json
```

## Controlled report build command

```cmd
python scripts\build_gold_multi_strategy_controlled_send_report.py --payload-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --out-dir data\research_results\gold_multi_strategy_controlled_send_report --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3" --account-name "Demo Account"
```

Observed:

```text
build_ok: true
reason: CONTROLLED_SEND_REPORT_BUILT
payload_rows: 1
include_ticket_result: false
```

Generated report:

```text
data/research_results/gold_multi_strategy_controlled_send_report/latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json
```

Generated payload copy:

```text
data/research_results/gold_multi_strategy_controlled_send_report/payload_bridge_send_controlled/order_payloads.csv
```

Payload metadata:

```text
broker_symbol=GOLD#
direction=BUY
lot=0.01
router_strategy_slot=BUY_C_ENV_RR2_72H
strategy_id=GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
signal_key=POLICY_TEST|same_direction_buy|BUY|0.01|BUY_C_ENV_RR2_72H
order_key=POLICY_TEST|same_direction_buy|BUY|0.01|BUY_C_ENV_RR2_72H|MOCHIPOYO_PAYLOAD
payload_key=POLICY_TEST|same_direction_buy|BUY|0.01|BUY_C_ENV_RR2_72H|MOCHIPOYO_PAYLOAD
```

Safety output:

```text
mt5_imported: false
order_check_called: false
order_send_called: false
real_sender_modified: false
existing_bat_modified: false
existing_mochipoyo_ledger_mutated: false
trigger_state_mutated: false
```

Decision:

```text
PASS.
```

## Send-report registry preview command

```cmd
python scripts\run_gold_multi_strategy_send_report_registry_preview.py --send-report-json data\research_results\gold_multi_strategy_controlled_send_report\latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --fallback-position-ticket-start 990001 --fallback-order-ticket-start 880001 --fallback-deal-ticket-start 770001 --fallback-account-login 75539039 --fallback-account-server "XMTrading-MT5 3" --position-status ACTIVE
```

Observed summary:

```text
cycle_ok: true
reason: SEND_REPORT_REGISTRY_PREVIEW_EVALUATED
payload_rows: 1
send_report_exists: true
```

Child steps:

```text
build_registry_from_send_report_payload: PASS, returncode=0
registry_reconcile_from_send_report: PASS, returncode=0
registry_policy_preview_from_send_report: PASS, returncode=0
```

Decision:

```text
PASS.
```

## Step 1: registry builder from send report

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
source_payload_csv=data/research_results/gold_multi_strategy_controlled_send_report/payload_bridge_send_controlled/order_payloads.csv
sender_report_json=data/research_results/gold_multi_strategy_controlled_send_report/latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json
```

Ticket source:

```text
position_ticket_source=fallback
order_ticket_source=fallback
deal_ticket_source=fallback
ticket_source=fallback_or_partial
used_fallback_ticket=true
```

This is expected because the controlled report did not claim real sent tickets.

Decision:

```text
PASS.
```

## Step 2: reconciliation from send report registry

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

## Step 3: registry-aware policy preview from send report

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

## Safety output

Validated safety counters:

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

Decision:

```text
PASS.
```

## Validation matrix

Current controlled send-report registry preview state:

```text
controlled payload-bearing send report generated: PASS
payload CSV copied and discoverable via payload_out_dir: PASS
send-report wrapper reads payload-bearing report: PASS
fallback synthetic tickets selected for no-real-send report: PASS
registry preview row generated from send report: PASS
registry row reconciles with mock position: PASS
registry-aware policy preview consumes generated registry: PASS
same_strategy BLOCK from generated registry row: PASS
all child steps returncode 0: PASS
read-only safety counters: PASS
```

## End-to-end validated chain

The following chain is now validated without running the real sender:

```text
controlled payload-bearing send-style report
→ payload CSV extraction
→ send metadata extraction
→ fallback ticket selection
→ registry preview row generation
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

## Design implication

The send-report registry preview wrapper is ready for payload-bearing reports.

It handles both validated cases:

```text
1. no-payload guarded send report:
   safe early exit, PASS

2. controlled payload-bearing send report:
   registry preview + reconcile + policy preview, PASS
```

## Current recommendation

Do not modify the real sender yet.

Next safe step:

```text
Update the next-chat handoff docs to record the completed registry/preflight/preview chain.
```

After that, the next design decision is whether to implement a sender-side dry-run-only registry write preview hook or continue keeping registry preview as a separate post-send-report wrapper.

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

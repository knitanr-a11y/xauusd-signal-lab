# GOLD multi-strategy controlled send-report with tickets validation

Last updated: 2026-05-10

## Purpose

This document records validation results for the controlled payload-bearing send-report path where the report includes ticket fields.

The validated purpose is to confirm that `scripts/run_gold_multi_strategy_send_report_registry_preview.py` prefers ticket values embedded in the send report over fallback synthetic ticket values.

Validated path:

```text
controlled payload-bearing send-style report with ticket fields
→ payload CSV extraction
→ mt5_report ticket extraction
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

## Controlled report build

Builder:

```text
scripts/build_gold_multi_strategy_controlled_send_report.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_controlled_send_report.py --payload-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --out-dir data\research_results\gold_multi_strategy_controlled_send_report_with_tickets --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3" --account-name "Demo Account" --include-ticket-result --position-ticket 990001 --order-ticket 880001 --deal-ticket 770001
```

Observed:

```text
build_ok: true
reason: CONTROLLED_SEND_REPORT_BUILT
payload_rows: 1
include_ticket_result: true
```

Generated report:

```text
data/research_results/gold_multi_strategy_controlled_send_report_with_tickets/latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json
```

Generated payload copy:

```text
data/research_results/gold_multi_strategy_controlled_send_report_with_tickets/payload_bridge_send_controlled/order_payloads.csv
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

Decision:

```text
PASS.
```

## Registry preview wrapper command

A short `--out-dir` was used to avoid Windows MAX_PATH issues under the deep MT5 Files directory.

```cmd
python scripts\run_gold_multi_strategy_send_report_registry_preview.py --send-report-json data\research_results\gold_multi_strategy_controlled_send_report_with_tickets\latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\r\ticket_preview --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --fallback-position-ticket-start 111111 --fallback-order-ticket-start 222222 --fallback-deal-ticket-start 333333 --fallback-account-login 75539039 --fallback-account-server "XMTrading-MT5 3" --position-status ACTIVE
```

Observed summary:

```text
cycle_ok: true
reason: SEND_REPORT_REGISTRY_PREVIEW_EVALUATED
send_report_exists: true
payload_rows: 1
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

## Ticket extraction validation

The wrapper was intentionally run with fallback ticket values that differ from report ticket values:

```text
fallback_position_ticket_start=111111
fallback_order_ticket_start=222222
fallback_deal_ticket_start=333333
```

The send report contained ticket fields:

```text
position_ticket=990001
order_ticket=880001
deal_ticket=770001
```

Observed send metadata:

```text
position_ticket_source=mt5_report.results[0].position_ticket
position_ticket_start=990001
order_ticket_source=mt5_report.results[0].order_ticket
order_ticket_start=880001
deal_ticket_source=mt5_report.results[0].deal_ticket
deal_ticket_start=770001
ticket_source=mt5_report
used_fallback_ticket=false
```

Decision:

```text
PASS.
```

This confirms fallback values were not used and report ticket fields were correctly preferred.

## Registry builder result

Observed:

```text
preview_ok: true
reason: REGISTRY_PREVIEW_ROWS_BUILT
rows_in: 1
rows_out_new: 1
rows_out_total: 1
validation_error_rows: 0
```

Generated registry row included:

```text
account_login=75539039
account_server=XMTrading-MT5 3
broker_symbol=GOLD#
symbol=GOLD
direction=BUY
lot=0.01
entry_price=4727.67
sl_price=4717.67
tp_price=4747.67
position_ticket=990001
order_ticket=880001
deal_ticket=770001
strategy_key=BUY_C_ENV_RR2_72H
strategy_alias=BUY_C
strategy_id=GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
position_status=ACTIVE
```

Decision:

```text
PASS.
```

## Reconciliation result

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

## Registry-aware policy preview result

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

Current controlled send-report-with-tickets state:

```text
controlled payload-bearing send report with ticket fields generated: PASS
send-report wrapper reads report and payload: PASS
report ticket fields preferred over fallback tickets: PASS
registry preview row uses report ticket values: PASS
registry row reconciles with mock position: PASS
registry-aware policy preview consumes generated registry: PASS
same_strategy BLOCK from generated registry row: PASS
all child steps returncode 0: PASS
read-only safety counters: PASS
```

## End-to-end validated chain

The following chain is now validated without running the real sender:

```text
controlled payload-bearing send-style report with tickets
→ payload CSV extraction
→ mt5_report ticket extraction
→ registry preview row generation
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

## Known Windows path note

Under the MT5 Files directory, deep output paths can trigger Windows MAX_PATH-style `FileNotFoundError` during JSON writes even when parent directories exist.

Observed workaround:

```text
Use a short --out-dir such as data/r/ticket_preview
```

Files already hardened with long-path output handling during this phase:

```text
scripts/build_gold_multi_strategy_controlled_send_report.py
scripts/run_gold_multi_strategy_send_report_registry_preview.py
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
```

The remaining candidate for hardening is:

```text
scripts/run_gold_multi_strategy_registry_policy_preview.py
```

The short `--out-dir` workaround confirmed the logic itself is correct.

## Current recommendation

Do not modify the real sender yet.

Next safe step:

```text
Either harden run_gold_multi_strategy_registry_policy_preview.py for Windows long paths,
or proceed to design a sender-side dry-run-only registry preview hook while keeping --out-dir short in validation commands.
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

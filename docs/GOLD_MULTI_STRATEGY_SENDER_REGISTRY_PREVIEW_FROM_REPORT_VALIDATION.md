# GOLD multi-strategy sender registry preview from report validation

Last updated: 2026-05-10

## Purpose

This document records validation for the sender-adjacent dry-run registry preview flow.

The validated flow does not modify `send_mt5_order_from_payload.py` yet. It consumes sender-style outputs and builds preview `position_registry` rows externally.

Validated scripts:

```text
scripts/build_gold_multi_strategy_controlled_sender_dry_run_report.py
scripts/build_gold_multi_strategy_sender_registry_preview_from_report.py
scripts/build_gold_multi_strategy_mock_positions_from_registry.py
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
```

## Safety boundary

No live trading operation was performed.

```text
No MetaTrader5 import in the new preview/build helper scripts.
No mt5.order_send.
No production position_registry.csv mutation.
No order ledger mutation.
No trigger-state mutation.
No existing Mochipoyo BAT modification.
```

The real sender remains unchanged:

```text
scripts/send_mt5_order_from_payload.py: not modified for registry write
```

## Background observations

A real sender dry-run report was found under:

```text
data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit/mt5_order_check_dry_run
```

It had:

```text
blocked_position_policy_rows=1
dry_run_check_ok_rows=0
error_rows=1
order_send_called_count=0
```

The sender-adjacent preview correctly produced no registry rows from this report:

```text
preview_ok=true
reason=NO_ELIGIBLE_SENDER_ROWS
sender_status_counts:
  BLOCKED_POSITION_POLICY: 1
eligible_sender_rows=0
registry_preview_rows=0
```

A later sender dry-run with relaxed policy passed position policy but failed local price validation due to stale SELL TP relative to current bid:

```text
order_status=BLOCKED_LOCAL_VALIDATION
validation_errors=SELL requires tp < bid: tp=5005.38; bid=4715.02
```

The preview hook correctly produced no registry row:

```text
preview_ok=true
reason=NO_ELIGIBLE_SENDER_ROWS
sender_status_counts:
  BLOCKED_LOCAL_VALIDATION: 1
eligible_sender_rows=0
registry_preview_rows=0
```

Decision:

```text
PASS for safe no-eligible handling.
```

## Controlled sender dry-run OK report

Builder:

```text
scripts/build_gold_multi_strategy_controlled_sender_dry_run_report.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_controlled_sender_dry_run_report.py --payload-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\order_payloads.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\controlled_sender_dry_run_ok --account-login 75539039 --account-server "XMTrading-MT5 3" --account-name "Demo Account" --broker-symbol GOLD# --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05
```

Observed:

```text
build_ok=true
reason=CONTROLLED_SENDER_DRY_RUN_REPORT_BUILT
rows_in=1
rows_out=1
dry_run_check_ok_rows=1
order_send_called_count=0
```

Controlled sender row:

```text
row_index=1
order_status=DRY_RUN_ORDER_CHECK_OK
broker_symbol=GOLD#
direction=SELL
lot=0.01
current_execution_price=5025.38
sl_price=5035.38
tp_price=5005.38
order_check_ok=true
order_send_called=false
```

Decision:

```text
PASS.
```

## Sender registry preview from report

Builder:

```text
scripts/build_gold_multi_strategy_sender_registry_preview_from_report.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_sender_registry_preview_from_report.py --sender-out-dir data\research_results\gold_multi_strategy_sender_registry_preview\controlled_sender_dry_run_ok --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok --position-ticket-start 990001 --order-ticket-start 880001 --deal-ticket-start 770001 --position-status ACTIVE
```

Observed:

```text
preview_ok=true
reason=REGISTRY_PREVIEW_ROWS_BUILT
sender_rows_in=1
payload_rows_in=1
eligible_sender_rows=1
registry_preview_rows=1
sender_status_counts:
  DRY_RUN_ORDER_CHECK_OK: 1
eligible_status_counts:
  DRY_RUN_ORDER_CHECK_OK: 1
send_requested_in_report=false
sender_order_send_called_count=0
```

Generated registry preview row:

```text
position_ticket=990001
order_ticket=880001
deal_ticket=770001
broker_symbol=GOLD#
direction=SELL
lot=0.01
entry_price=5025.38
sl_price=5035.38
tp_price=5005.38
strategy_key=SELL_H1H4_BEAR_AB
strategy_alias=SELL_AB
position_status=ACTIVE
signal_key=GOLD_H1H4_BEAR_M15_LOW_BREAK_B_ONLY_SAFE_FIXED10_RR2_12H|GOLD|SELL|B_ONLY_SAFE|2026-03-13 21:45:00|2026-03-13 21:45:00
```

Safety:

```text
mt5_imported=false
order_check_called_count=0
order_send_called_count=0
order_ledger_mutated=false
production_registry_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## Mismatch reconcile validation

A pre-existing SELL_AB scenario mock used ticket `990101`, while the generated registry row used ticket `990001`.

Observed:

```text
reconcile_ok=true
matched_active_registry_rows=0
matched_with_mismatch_rows=0
missing_position_rows=1
unregistered_position_rows=1
status_counts:
  REGISTRY_ACTIVE_MISSING_POSITION: 1
  POSITION_WITHOUT_ACTIVE_REGISTRY: 1
```

Interpretation:

```text
registry ticket 990001 was not found in current positions
position ticket 990101 was not present in ACTIVE registry rows
```

Decision:

```text
PASS for ticket mismatch detection.
```

## Mock positions from registry

Builder:

```text
scripts/build_gold_multi_strategy_mock_positions_from_registry.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_mock_positions_from_registry.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok\sender_registry_preview.csv --output-csv data\research_results\gold_multi_strategy_sender_registry_preview\mock_positions_from_sender_registry_preview.csv
```

Observed:

```text
build_ok=true
reason=MOCK_POSITIONS_BUILT_FROM_REGISTRY
registry_rows=1
active_registry_rows=1
rows_out=1
```

Generated mock position:

```text
ticket=990001
symbol=GOLD#
direction=SELL
volume=0.01
magic=26050601
comment=ms SELL_AB SELL_H1H4_BEAR_AB SE
```

Decision:

```text
PASS.
```

## Exact reconcile validation

Command:

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok\sender_registry_preview.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\mock_positions_from_sender_registry_preview.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok_reconcile_exact_match --symbol GOLD#
```

Observed:

```text
reconcile_ok=true
registry_status=REGISTRY_READ_OK
registry_rows=1
active_registry_rows=1
positions_rows=1
reconcile_rows=1
matched_active_registry_rows=1
matched_with_mismatch_rows=0
missing_position_rows=0
unregistered_position_rows=0
status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Row-level match:

```text
registry_position_ticket=990001
registry_strategy_key=SELL_H1H4_BEAR_AB
position_ticket=990001
position_symbol=GOLD#
position_direction=SELL
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

## Registry-aware policy preview from sender-generated registry

Command:

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\order_payloads.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\mock_positions_from_sender_registry_preview.csv --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok\sender_registry_preview.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok_policy_preview --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02
```

Observed:

```text
preview_ok=true
reason=POLICY_PREVIEW_EVALUATED
rows_in=1
rows_out=1
allow_rows=0
blocked_rows=1
same_strategy_blocked_rows=1
opposite_direction_blocked_rows=0
total_position_cap_blocked_rows=0
per_order_lot_blocked_rows=0
duplicate_key_blocked_rows=0
registry_inconsistency_blocked_rows=0
reconcile_status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Final policy decision:

```text
final_policy_decision=BLOCK
```

Final policy reason:

```text
same_strategy: ACTIVE matched registry position already exists for strategy=SELL_H1H4_BEAR_AB; tickets=['990001']
```

Decision:

```text
PASS.
```

## End-to-end validated chain

The following chain is now validated without modifying the real sender or writing production registry:

```text
controlled sender dry-run OK report
→ sender registry preview from report
→ registry-derived mock position
→ exact registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

## Safety matrix

```text
No real order_send: PASS
No new order_check from helper scripts: PASS
No production registry mutation: PASS
No order ledger mutation: PASS
No trigger-state mutation: PASS
Existing sender remains unchanged: PASS
Generated registry row schema compatible with reconciliation: PASS
Generated registry row schema compatible with policy preview: PASS
same_strategy BLOCK from sender-generated registry row: PASS
```

## Current implication

A sender-side dry-run-only registry preview hook concept is validated externally.

The next possible step is to decide whether to:

```text
A. keep this sender-adjacent external builder as the safe validation path for one more round, or
B. fold the preview hook directly into send_mt5_order_from_payload.py behind explicit disabled-by-default CLI flags.
```

Recommended next step:

```text
Keep external builder for one more validation round and document this result in the next-chat handoff addendum.
```

Do not modify yet:

```text
production position_registry.csv
existing Mochipoyo ledgers
existing trigger-state files
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
```

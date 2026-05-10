# GOLD multi-strategy fresh sender dry-run registry preview validation

Last updated: 2026-05-10

## Purpose

This document records validation for a fresh, non-stale MT5-tick-based payload flowing through the real sender dry-run and sender-adjacent registry preview cycle.

Validated chain:

```text
current MT5 tick
→ fresh sender-valid payload
→ send_mt5_order_from_payload.py dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender registry preview row
→ registry-derived mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
```

The real sender was not modified.

## Safety boundary

```text
No --send was passed.
No real mt5.order_send was called.
No production position_registry.csv was written.
No existing order ledger was mutated.
No trigger-state file was mutated.
No existing Mochipoyo BAT was modified.
```

The fresh payload builder does initialize MT5 and reads account/symbol/tick metadata only.

It does not call:

```text
mt5.order_check
mt5.order_send
```

## Fresh payload builder

Script:

```text
scripts/build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick.py --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload --broker-symbol GOLD# --symbol GOLD --direction SELL --lot 0.01 --sl-distance 10 --tp-distance 20 --expected-login 75539039 --require-demo-account --select-symbol
```

Observed:

```text
build_ok=true
reason=FRESH_SENDER_VALID_PAYLOAD_BUILT
rows_out=1
initialize_ok=true
symbol_select_ok=true
```

Observed tick/price relation:

```text
bid=4715.02
ask=4715.97
entry=4715.02
sl=4725.02
tp=4695.02
validation_errors=[]
```

Generated payload:

```text
broker_symbol=GOLD#
direction=SELL
lot=0.01
entry_price_reference=4715.02
sl_price=4725.02
tp_price=4695.02
strategy_id=GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
router_strategy_slot=SELL_H1H4_BEAR_AB
signal_key=FRESH_SENDER_VALID|SELL_H1H4_BEAR_AB|GOLD|SELL|B_ONLY_SAFE|20260510T001734Z
order_key=FRESH_SENDER_VALID|SELL_H1H4_BEAR_AB|GOLD|SELL|B_ONLY_SAFE|20260510T001734Z|MOCHIPOYO_PAYLOAD
```

Safety:

```text
mt5_imported=true
order_check_called_count=0
order_send_called_count=0
ledger_mutated=false
trigger_state_mutated=false
production_registry_mutated=false
```

Decision:

```text
PASS.
```

## One-command sender dry-run registry preview cycle

Wrapper:

```text
scripts/run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py
```

Command:

```cmd
python scripts\run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py --input-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\order_payloads.csv --order-ledger-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --require-demo-account --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05
```

Observed:

```text
cycle_ok=true
reason=SENDER_DRY_RUN_REGISTRY_PREVIEW_EVALUATED
send_requested=false
sender_outputs_exist=true
```

Sender metrics:

```text
rows_in=1
rows_out=1
dry_run_check_ok_rows=1
sent_rows=0
blocked_position_policy_rows=0
error_rows=0
order_send_called_count=0
```

Registry preview:

```text
registry_preview_ok=true
registry_preview_reason=REGISTRY_PREVIEW_ROWS_BUILT
registry_preview_rows=1
```

Step table:

```text
sender_dry_run: ok=true, returncode=0
sender_registry_preview_from_report: ok=true, returncode=0
```

Safety:

```text
wrapper_passed_send_flag=false
production_registry_mutated=false
trigger_state_mutated=false
existing_sender_modified=false
```

Decision:

```text
PASS.
```

## Registry-derived mock position

Script:

```text
scripts/build_gold_multi_strategy_mock_positions_from_registry.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_mock_positions_from_registry.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\sender_registry_preview\sender_registry_preview.csv --output-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\mock_positions_from_registry.csv
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
external_id=SELL_H1H4_BEAR_AB|FRESH_SENDER_VALID|SELL_H1H4_BEAR_AB|GOLD|SELL|B_ONLY_SAFE|20260510T001734Z
```

Safety:

```text
mt5_imported=false
order_check_called=false
order_send_called=false
ledger_written=false
registry_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## Exact reconcile

Script:

```text
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
```

Command:

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\sender_registry_preview\sender_registry_preview.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\mock_positions_from_registry.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any_reconcile_exact --symbol GOLD#
```

Observed:

```text
reconcile_ok=true
reason=RECONCILE_EVALUATED
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

Safety:

```text
order_check_called_count=0
order_send_called_count=0
ledger_mutated=false
registry_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## Registry-aware policy preview

Script:

```text
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
```

Command:

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py --input-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\order_payloads.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\mock_positions_from_registry.csv --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\sender_registry_preview\sender_registry_preview.csv --order-ledger-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any_policy_preview --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02
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

Final decision:

```text
final_policy_decision=BLOCK
```

Final reason:

```text
same_strategy: ACTIVE matched registry position already exists for strategy=SELL_H1H4_BEAR_AB; tickets=['990001']
```

Safety:

```text
mt5_imported=false
order_check_called_count=0
order_send_called_count=0
ledger_mutated=false
registry_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## End-to-end validated chain

```text
fresh MT5 tick-based payload
→ send_mt5_order_from_payload.py dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender registry preview row generated
→ registry-derived mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
```

Decision:

```text
PASS.
```

## Current implication

The wrapper path is now validated in both important cases:

```text
1. stale/blocked payload: NO_ELIGIBLE_SENDER_ROWS, cycle_ok=true
2. fresh sender-valid payload: DRY_RUN_ORDER_CHECK_OK, registry_preview_rows=1, policy same_strategy BLOCK
```

This makes the wrapper a strong candidate to keep as the next safe integration layer before modifying the real sender or writing production registry.

## Recommended next step

Do not write production registry yet.

Recommended next step:

```text
Use the fresh-payload validated wrapper path as the reference behavior, then decide whether to keep wrapper-only or fold a disabled-by-default preview hook into send_mt5_order_from_payload.py.
```

Do not modify yet:

```text
production position_registry.csv
existing Mochipoyo ledgers
existing trigger-state files
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
close intent MT5 execution
BTC router/send integration
```

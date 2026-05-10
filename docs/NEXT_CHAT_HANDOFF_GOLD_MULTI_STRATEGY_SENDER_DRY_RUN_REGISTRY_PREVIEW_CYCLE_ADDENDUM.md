# NEXT CHAT HANDOFF ADDENDUM - sender dry-run registry preview cycle

Last updated: 2026-05-10

## Read this together with

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE_LONGPATH_ADDENDUM.md
docs/GOLD_MULTI_STRATEGY_SENDER_REGISTRY_PREVIEW_FROM_REPORT_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_FRESH_SENDER_DRY_RUN_REGISTRY_PREVIEW_VALIDATION.md
```

## Why this addendum exists

After the sender-registry preview validation doc was updated, additional one-command wrapper validations were completed.

New wrapper:

```text
scripts/run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py
```

Fresh payload builder:

```text
scripts/build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick.py
```

Purpose:

```text
send_mt5_order_from_payload.py dry-run
→ sender report/results
→ sender-adjacent registry preview from report
```

Important safety boundary:

```text
The wrapper never passes --send.
The real sender script remains unchanged.
Production position_registry.csv is not written.
Existing Mochipoyo ledger files are not mutated by helper scripts.
Trigger-state files are not mutated.
Existing Mochipoyo BAT files are not modified.
```

## Implementation update

Initial wrapper behavior stopped when `send_mt5_order_from_payload.py` returned non-zero.

However, the sender returns non-zero when rows are blocked by local validation or position policy even when it still writes valid outputs:

```text
mt5_order_send_report.json
mt5_order_send_results.csv
```

The wrapper was updated so that:

```text
If sender returncode != 0 but report/results exist,
continue to registry-preview evaluation.
```

This allows safe blocked-output validation such as:

```text
BLOCKED_LOCAL_VALIDATION
→ NO_ELIGIBLE_SENDER_ROWS
```

Implementation commit:

```text
16fe4a9216dc432d5afe7c0d297dc5c2ea930618
```

## Validation 1: stale real payload blocked but safely evaluated

Validated command:

```cmd
python scripts\run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\order_payloads.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_real_payload_allow_any --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --require-demo-account --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05
```

Observed result:

```text
cycle_ok=true
reason=SENDER_DRY_RUN_BLOCKED_BUT_REGISTRY_PREVIEW_EVALUATED
send_requested=false
sender_outputs_exist=true
```

Sender metrics:

```text
rows_in=1
rows_out=1
dry_run_check_ok_rows=0
sent_rows=0
blocked_position_policy_rows=0
error_rows=1
order_send_called_count=0
```

Registry preview result:

```text
registry_preview_ok=true
registry_preview_reason=NO_ELIGIBLE_SENDER_ROWS
registry_preview_rows=0
```

Step table:

```text
sender_dry_run: ok=false, returncode=1
sender_registry_preview_from_report: ok=true, returncode=0
```

Interpretation:

```text
The real stale payload was still blocked by sender local validation.
The wrapper correctly consumed the generated sender report/results.
The registry-preview builder correctly produced no rows.
The cycle was considered evaluated and safe.
```

Decision:

```text
PASS.
```

## Validation 2: fresh MT5-tick payload reaches DRY_RUN_ORDER_CHECK_OK naturally

Validation doc:

```text
docs/GOLD_MULTI_STRATEGY_FRESH_SENDER_DRY_RUN_REGISTRY_PREVIEW_VALIDATION.md
```

Fresh payload builder command:

```cmd
python scripts\build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick.py --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload --broker-symbol GOLD# --symbol GOLD --direction SELL --lot 0.01 --sl-distance 10 --tp-distance 20 --expected-login 75539039 --require-demo-account --select-symbol
```

Observed payload build:

```text
build_ok=true
reason=FRESH_SENDER_VALID_PAYLOAD_BUILT
rows_out=1
initialize_ok=true
symbol_select_ok=true
```

Observed MT5 tick / price relation:

```text
bid=4715.02
ask=4715.97
entry=4715.02
sl=4725.02
tp=4695.02
validation_errors=[]
```

Fresh payload:

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
```

Fresh wrapper command:

```cmd
python scripts\run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py --input-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\order_payloads.csv --order-ledger-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --require-demo-account --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05
```

Observed wrapper result:

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

Registry preview result:

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

Decision:

```text
PASS.
```

## Validation 3: fresh registry row exact reconcile and same_strategy BLOCK

Registry-derived mock command:

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

Mock position:

```text
ticket=990001
symbol=GOLD#
direction=SELL
volume=0.01
magic=26050601
comment=ms SELL_AB SELL_H1H4_BEAR_AB SE
external_id=SELL_H1H4_BEAR_AB|FRESH_SENDER_VALID|SELL_H1H4_BEAR_AB|GOLD|SELL|B_ONLY_SAFE|20260510T001734Z
```

Reconcile command:

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\sender_registry_preview\sender_registry_preview.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\mock_positions_from_registry.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any_reconcile_exact --symbol GOLD#
```

Observed reconcile:

```text
reconcile_ok=true
matched_active_registry_rows=1
matched_with_mismatch_rows=0
missing_position_rows=0
unregistered_position_rows=0
status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Row-level match:

```text
ticket_match=true
symbol_match=true
direction_match=true
lot_match=true
strategy_detected_in_position=true
reconcile_status=REGISTRY_ACTIVE_MATCHED
```

Policy preview command:

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py --input-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\order_payloads.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\mock_positions_from_registry.csv --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any\sender_registry_preview\sender_registry_preview.csv --order-ledger-csv data\research_results\gold_multi_strategy_sender_registry_preview\fresh_sender_valid_payload\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_fresh_payload_allow_any_policy_preview --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02
```

Observed policy preview:

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
final_policy_reason=same_strategy: ACTIVE matched registry position already exists for strategy=SELL_H1H4_BEAR_AB; tickets=['990001']
```

Decision:

```text
PASS.
```

## Safety observations

```text
wrapper_passed_send_flag=false
send_requested=false
order_send_called_count=0
production_registry_mutated=false
trigger_state_mutated=false
existing_sender_modified=false
ledger_mutated=false
registry_mutated=false
```

Decision:

```text
PASS.
```

## Current implication

The project now has a one-command, sender-adjacent dry-run registry preview validation path:

```text
scripts/run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py
```

This wrapper path is validated in both important cases:

```text
1. stale/blocked payload
   → NO_ELIGIBLE_SENDER_ROWS
   → cycle_ok=true

2. fresh sender-valid payload
   → DRY_RUN_ORDER_CHECK_OK
   → registry_preview_rows=1
   → exact reconcile
   → same_strategy BLOCK
```

This is safer than modifying the real sender immediately.

Recommended next step:

```text
Keep this wrapper as the next integration layer for one more round.
Then decide whether to fold disabled-by-default registry preview flags into send_mt5_order_from_payload.py.
```

Do not modify yet:

```text
production position_registry.csv
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
close intent MT5 execution
BTC router/send integration
```

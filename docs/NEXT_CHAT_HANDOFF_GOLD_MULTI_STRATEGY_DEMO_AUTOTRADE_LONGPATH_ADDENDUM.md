# NEXT CHAT HANDOFF ADDENDUM - GOLD multi-strategy demo autotrade long-path / ticket / sender-registry validation

Last updated: 2026-05-10

## Read this together with

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE.md
docs/GOLD_MULTI_STRATEGY_CONTROLLED_SEND_REPORT_WITH_TICKETS_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_REGISTRY_POLICY_PREVIEW_LONGPATH_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_SENDER_REGISTRY_PREVIEW_FROM_REPORT_VALIDATION.md
```

## Why this addendum exists

After the main handoff was updated, three additional validations were completed:

```text
1. controlled payload-bearing send report with ticket fields included: PASS
2. registry policy preview long-path wrapper: PASS
3. sender-adjacent registry preview from sender-style report/results: PASS
```

These should be treated as part of the current state for the next chat.

## Newly completed validation: controlled send report with tickets

Validation doc:

```text
docs/GOLD_MULTI_STRATEGY_CONTROLLED_SEND_REPORT_WITH_TICKETS_VALIDATION.md
```

Builder:

```text
scripts/build_gold_multi_strategy_controlled_send_report.py
```

Wrapper:

```text
scripts/run_gold_multi_strategy_send_report_registry_preview.py
```

Validated command pattern:

```cmd
python scripts\build_gold_multi_strategy_controlled_send_report.py --payload-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --out-dir data\research_results\gold_multi_strategy_controlled_send_report_with_tickets --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3" --account-name "Demo Account" --include-ticket-result --position-ticket 990001 --order-ticket 880001 --deal-ticket 770001
```

Then:

```cmd
python scripts\run_gold_multi_strategy_send_report_registry_preview.py --send-report-json data\research_results\gold_multi_strategy_controlled_send_report_with_tickets\latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\r\ticket_preview --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --fallback-position-ticket-start 111111 --fallback-order-ticket-start 222222 --fallback-deal-ticket-start 333333 --fallback-account-login 75539039 --fallback-account-server "XMTrading-MT5 3" --position-status ACTIVE
```

Observed:

```text
cycle_ok: true
reason: SEND_REPORT_REGISTRY_PREVIEW_EVALUATED
payload_rows: 1
build_registry_from_send_report_payload: PASS
registry_reconcile_from_send_report: PASS
registry_policy_preview_from_send_report: PASS
```

Ticket extraction was the key validation:

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

This confirms fallback ticket values were not used:

```text
fallback_position_ticket_start=111111
fallback_order_ticket_start=222222
fallback_deal_ticket_start=333333
```

Registry row generated:

```text
position_ticket=990001
order_ticket=880001
deal_ticket=770001
strategy_key=BUY_C_ENV_RR2_72H
strategy_alias=BUY_C
position_status=ACTIVE
```

Reconciliation result:

```text
reconcile_ok: true
matched_active_registry_rows: 1
missing_position_rows: 0
unregistered_position_rows: 0
status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Policy preview result:

```text
preview_ok: true
blocked_rows: 1
same_strategy_blocked_rows: 1
registry_inconsistency_blocked_rows: 0
final_policy_decision=BLOCK
final_policy_reason=same_strategy: ACTIVE matched registry position already exists for strategy=BUY_C_ENV_RR2_72H; tickets=['990001']
```

Safety:

```text
mt5_imported=false
order_check_called_count=0
order_send_called_count=0
registry_mutated=false
ledger_mutated=false
trigger_state_mutated=false
real_sender_modified=false
existing_bat_modified=false
```

Decision:

```text
PASS.
```

## Newly completed validation: registry policy preview long-path wrapper

Validation doc:

```text
docs/GOLD_MULTI_STRATEGY_REGISTRY_POLICY_PREVIEW_LONGPATH_VALIDATION.md
```

New script:

```text
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
```

Commit:

```text
bad367d69dbe5cf21cf85050f0068a475f998042
```

This wrapper imports the validated base policy module and monkey-patches file IO only:

```text
base policy logic: unchanged
file existence checks: windows_long_path-aware
CSV writes: windows_long_path-aware
JSON writes: windows_long_path-aware
```

Validated command:

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py --input-csv data\research_results\gold_multi_strategy_controlled_send_report_with_tickets\payload_bridge_send_controlled\order_payloads.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --registry-csv data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\position_registry_from_send_report_preview.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets --output-csv data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\registry_policy_preview_from_send_report_longpath.csv --output-json data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\registry_policy_preview_from_send_report_longpath.json --reconcile-csv data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\registry_policy_preview_reconcile_from_send_report_longpath.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02
```

Observed:

```text
preview_ok: true
reason: POLICY_PREVIEW_EVALUATED
rows_in: 1
rows_out: 1
allow_rows: 0
blocked_rows: 1
same_strategy_blocked_rows: 1
registry_inconsistency_blocked_rows: 0
```

Final decision:

```text
final_policy_decision=BLOCK
final_policy_reason=same_strategy: ACTIVE matched registry position already exists for strategy=BUY_C_ENV_RR2_72H; tickets=['990001']
```

Safety:

```text
mt5_imported=false
order_check_called_count=0
order_send_called_count=0
registry_mutated=false
ledger_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## Newly completed validation: sender registry preview from report

Validation doc:

```text
docs/GOLD_MULTI_STRATEGY_SENDER_REGISTRY_PREVIEW_FROM_REPORT_VALIDATION.md
```

New helper scripts:

```text
scripts/find_gold_multi_strategy_sender_report_outputs.py
scripts/build_gold_multi_strategy_controlled_sender_dry_run_report.py
scripts/build_gold_multi_strategy_sender_registry_preview_from_report.py
scripts/build_gold_multi_strategy_mock_positions_from_registry.py
```

Important boundary:

```text
scripts/send_mt5_order_from_payload.py was not modified.
production position_registry.csv was not written.
existing order ledgers were not mutated by these helpers.
trigger-state files were not mutated.
```

### Real sender-output discovery

Finder:

```text
scripts/find_gold_multi_strategy_sender_report_outputs.py
```

Observed one existing sender output directory:

```text
data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit/mt5_order_check_dry_run
```

Observed counts:

```text
blocked_position_policy_rows=1
dry_run_check_ok_rows=0
error_rows=1
order_send_called_count=0
```

The sender-adjacent preview correctly produced no registry rows from this blocked report:

```text
preview_ok=true
reason=NO_ELIGIBLE_SENDER_ROWS
sender_status_counts:
  BLOCKED_POSITION_POLICY: 1
eligible_sender_rows=0
registry_preview_rows=0
```

A later sender dry-run with relaxed position policy passed position policy but failed local price validation due to a stale SELL payload:

```text
order_status=BLOCKED_LOCAL_VALIDATION
validation_errors=SELL requires tp < bid: tp=5005.38; bid=4715.02
```

The preview hook correctly produced no registry row from this blocked local-validation result:

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

### Controlled sender dry-run OK report

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

### Sender registry preview row from report

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

Decision:

```text
PASS.
```

### Ticket mismatch reconcile check

A pre-existing `same_strategy_sell_ab` mock used ticket `990101`, while the sender-generated registry row used ticket `990001`.

Observed:

```text
reconcile_ok=true
matched_active_registry_rows=0
missing_position_rows=1
unregistered_position_rows=1
status_counts:
  REGISTRY_ACTIVE_MISSING_POSITION: 1
  POSITION_WITHOUT_ACTIVE_REGISTRY: 1
```

Decision:

```text
PASS for ticket mismatch detection.
```

### Exact match reconcile from registry-derived mock

Builder:

```text
scripts/build_gold_multi_strategy_mock_positions_from_registry.py
```

Command:

```cmd
python scripts\build_gold_multi_strategy_mock_positions_from_registry.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok\sender_registry_preview.csv --output-csv data\research_results\gold_multi_strategy_sender_registry_preview\mock_positions_from_sender_registry_preview.csv
```

Observed mock position:

```text
ticket=990001
symbol=GOLD#
direction=SELL
volume=0.01
magic=26050601
comment=ms SELL_AB SELL_H1H4_BEAR_AB SE
```

Reconcile command:

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok\sender_registry_preview.csv --positions-csv data\research_results\gold_multi_strategy_sender_registry_preview\mock_positions_from_sender_registry_preview.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\from_controlled_sender_dry_run_ok_reconcile_exact_match --symbol GOLD#
```

Observed:

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

Decision:

```text
PASS.
```

### Registry-aware policy preview from sender-generated registry

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
final_policy_reason=same_strategy: ACTIVE matched registry position already exists for strategy=SELL_H1H4_BEAR_AB; tickets=['990001']
```

Decision:

```text
PASS.
```

## Current combined registry/send-report/sender-preview state

As of this addendum, the following are validated:

```text
preflight v2/v3: PASS
registry reconcile: PASS
registry-aware policy preview: PASS
registry row from payload preview: PASS
one-command demo send registry preview cycle: PASS
send-report registry preview no-payload path: PASS
controlled payload-bearing send report without tickets: PASS
controlled payload-bearing send report with tickets: PASS
send report ticket extraction prefers mt5_report over fallback: PASS
long-path policy preview output under deep MT5 Files path: PASS
sender-output discovery helper: PASS
sender-adjacent preview no-eligible handling for BLOCKED_POSITION_POLICY: PASS
sender-adjacent preview no-eligible handling for BLOCKED_LOCAL_VALIDATION: PASS
controlled sender dry-run OK report fixture: PASS
sender registry preview row from DRY_RUN_ORDER_CHECK_OK report: PASS
registry-derived mock position exact reconcile: PASS
policy preview same_strategy BLOCK from sender-generated registry row: PASS
```

## Windows path note

Deep paths under:

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\...\MQL5\Files\xauusd-signal-lab
```

can trigger `FileNotFoundError` during normal `Path.write_text()` even when parent folders exist.

Already hardened or wrapped during this phase:

```text
scripts/build_gold_multi_strategy_controlled_send_report.py
scripts/run_gold_multi_strategy_send_report_registry_preview.py
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
scripts/build_gold_multi_strategy_sender_registry_preview_from_report.py
scripts/build_gold_multi_strategy_controlled_sender_dry_run_report.py
scripts/build_gold_multi_strategy_mock_positions_from_registry.py
scripts/find_gold_multi_strategy_sender_report_outputs.py
```

The preferred short workaround remains valid for quick tests:

```text
--out-dir data\r\ticket_preview
```

## Recommended next task

Do not modify the production registry yet.

The sender-adjacent dry-run registry preview concept is now validated externally.

Next safe design decision:

```text
A. keep this sender-adjacent external builder as the safe validation path for one more round, or
B. fold the preview hook directly into send_mt5_order_from_payload.py behind explicit disabled-by-default CLI flags.
```

If moving to B, use explicit disabled-by-default CLI flags such as:

```text
--registry-preview-out-csv <path>
--registry-preview-out-json <path>
--registry-preview-position-status ACTIVE
--registry-preview-position-ticket-start 990001
--registry-preview-order-ticket-start 880001
--registry-preview-deal-ticket-start 770001
```

Still do not write production registry yet.

Do not modify yet:

```text
production position_registry.csv
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
close intent MT5 execution
BTC router/send integration
```

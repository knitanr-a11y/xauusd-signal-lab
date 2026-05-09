# NEXT CHAT HANDOFF ADDENDUM - GOLD multi-strategy demo autotrade long-path / ticket validation

Last updated: 2026-05-10

## Read this together with

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE.md
docs/GOLD_MULTI_STRATEGY_CONTROLLED_SEND_REPORT_WITH_TICKETS_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_REGISTRY_POLICY_PREVIEW_LONGPATH_VALIDATION.md
```

## Why this addendum exists

After the main handoff was updated, two additional validations were completed:

```text
1. controlled payload-bearing send report with ticket fields included: PASS
2. registry policy preview long-path wrapper: PASS
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

## Current combined registry/send-report state

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
```

The preferred short workaround remains valid for quick tests:

```text
--out-dir data\r\ticket_preview
```

But the long-path wrapper confirms policy preview itself can now write to the deeper research output path.

## Recommended next task

Do not modify the real sender yet.

Next safe design step:

```text
Design sender-side dry-run-only registry preview hook.
```

Suggested intent:

```text
send_mt5_order_from_payload.py reads payload and, without sending, emits the registry row it would write after a successful real/demo order_send.
```

Suggested CLI concept:

```text
--registry-preview-out-csv <path>
--registry-preview-out-json <path>
```

Still do not write production registry yet.

Do not modify yet:

```text
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
production position_registry.csv
```

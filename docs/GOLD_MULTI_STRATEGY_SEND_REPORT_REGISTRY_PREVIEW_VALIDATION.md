# GOLD multi-strategy send-report registry preview validation

Last updated: 2026-05-09

## Purpose

This document records validation results for reading an existing guarded demo send-cycle report and using it as the starting point for registry preview.

The target flow is:

```text
guarded demo send-cycle report
→ locate payload CSV used by that report
→ extract send/account/ticket metadata if available
→ build preview registry row when payload rows exist
→ reconcile
→ registry-aware policy preview
```

This script does not run the guarded send cycle itself. It only reads an already-created report.

## Safety boundary

This validation is read-only and non-executing.

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

## Implemented script

```text
scripts/run_gold_multi_strategy_send_report_registry_preview.py
```

Commit:

```text
f25948974e9020df1b8626418b711eea394edb65
```

Primary input:

```text
data/research_results/gold_multi_strategy_demo_autotrade_send_cycle/latest_multi_strategy_demo_autotrade_send_cycle_result.json
```

Primary outputs:

```text
data/research_results/gold_multi_strategy_send_report_registry_preview/send_report_registry_preview_summary.json
data/research_results/gold_multi_strategy_send_report_registry_preview/send_report_registry_preview_summary.csv
data/research_results/gold_multi_strategy_send_report_registry_preview/position_registry_from_send_report_preview.csv
data/research_results/gold_multi_strategy_send_report_registry_preview/position_registry_reconcile_from_send_report.csv
data/research_results/gold_multi_strategy_send_report_registry_preview/registry_policy_preview_from_send_report.csv
```

## Validation command

```cmd
python scripts\run_gold_multi_strategy_send_report_registry_preview.py --send-report-json data\research_results\gold_multi_strategy_demo_autotrade_send_cycle\latest_multi_strategy_demo_autotrade_send_cycle_result.json --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_send_report_registry_preview --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --fallback-position-ticket-start 990001 --fallback-order-ticket-start 880001 --fallback-deal-ticket-start 770001 --fallback-account-login 75539039 --fallback-account-server "XMTrading-MT5 3" --position-status ACTIVE
```

## Observed result

Observed summary:

```text
cycle_ok: true
reason: NO_PAYLOAD_ROWS_IN_SEND_REPORT_PAYLOAD_CSV
send_report_exists: true
payload_rows: 0
steps: []
```

The script correctly located the payload CSV referenced by the guarded send report:

```text
payload_csv=data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_send/order_payloads.csv
```

The source guarded send-cycle metrics were read correctly:

```text
source_cycle_ok: true
source_send_enabled: true
source_safe_send_guard_ok: true
source_send_requested: false
source_payload_rows_out: 0
source_mt5_order_send_called_count: 0
source_mt5_sent_rows: 0
source_mt5_blocked_position_policy_rows: 0
source_mt5_status_summary: NO_MT5_ROWS
```

Because there were no payload rows, the script correctly skipped child preview stages:

```text
registry preview row generation: SKIPPED
registry reconciliation: SKIPPED
registry-aware policy preview: SKIPPED
```

This is expected and correct for a no-signal / no-payload guarded send report.

Decision:

```text
PASS.
```

## Send metadata extraction

The no-payload report did not contain real send tickets, so fallback metadata was selected:

```text
account_login: 75539039
account_server: XMTrading-MT5 3
position_ticket_start: 990001
order_ticket_start: 880001
deal_ticket_start: 770001
position_ticket_source: fallback
order_ticket_source: fallback
deal_ticket_source: fallback
ticket_source: fallback_or_partial
used_fallback_ticket: true
```

This is expected for a no-send/no-ticket report.

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

Current send-report registry preview validation state:

```text
guarded send report exists and is readable: PASS
payload CSV path extracted from report payload_out_dir: PASS
no-payload safe early exit: PASS
source send-cycle metrics extracted: PASS
fallback ticket metadata selected for no-send report: PASS
child registry preview stages skipped when payload_rows=0: PASS
read-only safety counters: PASS
```

## Not yet validated

The following path still needs a payload-bearing send report:

```text
guarded demo send report with payload rows
→ registry preview row generation
→ reconciliation
→ registry-aware policy preview
```

This was not reached in this validation because the latest guarded send report had:

```text
payload_rows: 0
source_payload_rows_out: 0
source_send_requested: false
```

## Design implication

The wrapper is ready to consume a real guarded send-cycle report.

For no-payload cycles, it exits safely and records the reason.

For future payload-bearing cycles, it should continue into:

```text
build_gold_multi_strategy_position_registry_from_payload_preview.py
run_gold_multi_strategy_position_registry_reconcile_dry_run.py
run_gold_multi_strategy_registry_policy_preview.py
```

## Current recommendation

Do not modify the real sender yet.

Next safe step:

```text
Wait for or create a controlled payload-bearing guarded send report in dry-run/no-send mode,
then run scripts/run_gold_multi_strategy_send_report_registry_preview.py again.
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

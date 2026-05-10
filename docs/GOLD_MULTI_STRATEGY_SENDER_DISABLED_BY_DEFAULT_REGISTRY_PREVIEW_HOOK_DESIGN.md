# GOLD multi-strategy sender disabled-by-default registry preview hook design

Last updated: 2026-05-10

## Purpose

Design a disabled-by-default registry preview hook for:

```text
scripts/send_mt5_order_from_payload.py
```

This is a design document only. It does not modify the real sender.

The current canonical safe validation path remains:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
python scripts\verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py --summary-json data\r\ff\summary.json --out-json data\r\ff\summary_verify.json --out-csv data\r\ff\summary_verify_checks.csv
```

## Current validated state

The wrapper/BAT/verifier path is validated:

```text
fresh MT5 tick payload
→ real sender dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender registry preview row
→ registry-derived mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
→ read-only summary verification
```

Validated safety:

```text
--send not passed
order_send_called_count=0
production position_registry.csv not written
existing Mochipoyo ledgers not mutated
trigger-state not mutated
existing production BAT not modified
sender script not modified for registry writes yet
```

## Why not write production registry yet

The registry row is currently validated as a preview artifact only.

Production registry writing should wait until all of these are true:

```text
1. disabled-by-default preview hook is validated inside sender dry-run
2. preview rows match the external builder output
3. actual demo-send path is separately guarded and verified
4. position reconciliation against real MT5 positions is stable
5. close intent / lifecycle update design is defined
```

## Proposed sender CLI flags

All new behavior must be disabled by default.

Suggested flags:

```text
--registry-preview-out-csv <path>
--registry-preview-out-json <path>
--registry-preview-position-status ACTIVE
--registry-preview-position-ticket-start 990001
--registry-preview-order-ticket-start 880001
--registry-preview-deal-ticket-start 770001
--registry-preview-include-dry-run-check-ok
--registry-preview-include-sent
```

Recommended defaults:

```text
registry_preview_out_csv = None
registry_preview_out_json = None
registry_preview_position_status = ACTIVE
registry_preview_position_ticket_start = 990001
registry_preview_order_ticket_start = 880001
registry_preview_deal_ticket_start = 770001
registry_preview_include_dry_run_check_ok = true
registry_preview_include_sent = false
```

Important:

```text
If neither --registry-preview-out-csv nor --registry-preview-out-json is provided,
no registry preview work is performed.
```

## Eligibility rules for preview rows

For dry-run validation, eligible sender results are:

```text
order_status == DRY_RUN_ORDER_CHECK_OK
```

For future guarded demo send validation, optional eligible sender results may include:

```text
order_status == SENT
order_send_ok == true
```

But `SENT` rows should only be included if explicitly enabled:

```text
--registry-preview-include-sent
```

Rows that must not produce registry preview rows:

```text
BLOCKED_POSITION_POLICY
BLOCKED_LOCAL_VALIDATION
BLOCKED_DUPLICATE
ERROR_*
NO_MT5_ROWS
NO_INPUT_ROWS
```

## Required source fields

The sender result row and/or original payload row must provide:

```text
broker_symbol
symbol or broker_symbol
direction
lot
current_execution_price or entry_price_reference or entry_price
sl_price
tp_price
order_key or payload_key
signal_key
strategy_id / router_strategy_id
router_strategy_slot / pair_name / strategy_key
condition_id, when available
magic_number, when available
comment, when available
```

## Strategy key mapping

The sender preview hook should use the same strategy key extraction behavior as the external builder.

Priority:

```text
1. router_strategy_slot
2. strategy_key
3. pair_name
4. inferred from strategy_id
```

Known mappings:

```text
BUY_C_ENV_RR2_72H
SELL_H1H4_BEAR_AB
```

Aliases:

```text
BUY_C_ENV_RR2_72H -> BUY_C
SELL_H1H4_BEAR_AB -> SELL_AB
```

## Ticket behavior

For dry-run rows, no real ticket exists. Use deterministic preview tickets:

```text
position_ticket = position_ticket_start + eligible_row_index
order_ticket = order_ticket_start + eligible_row_index
deal_ticket = deal_ticket_start + eligible_row_index
```

For future sent rows, prefer actual sender/MT5 result tickets when present:

```text
position_ticket from mt5 result position/deal/order metadata if available
order_ticket from mt5 result order
deal_ticket from mt5 result deal
```

Fallback tickets should be clearly marked:

```text
ticket_source=fallback_preview
```

Actual ticket source should be marked:

```text
ticket_source=mt5_report
```

## Output schema

Preview CSV/JSON should contain at least:

```text
schema_version
position_ticket
order_ticket
deal_ticket
ticket_source
account_login
account_server
broker_symbol
symbol
direction
lot
entry_price
sl_price
tp_price
strategy_key
strategy_alias
strategy_id
condition_id
signal_key
order_key
payload_key
magic_number
comment
position_status
source_sender_status
source_sender_row_index
source_payload_row_index
created_at_utc
```

Schema version:

```text
gold_multi_strategy_sender_registry_preview_from_sender_v1
```

## Safety rules

The sender hook must never write production registry.

Allowed outputs:

```text
--registry-preview-out-csv path
--registry-preview-out-json path
```

Forbidden outputs:

```text
production position_registry.csv
existing Mochipoyo ledgers
trigger-state files
```

The hook must not change order execution behavior.

The hook must run after sender result rows are already determined:

```text
payload read
→ local validation
→ position policy
→ order_check/order_send logic
→ results rows
→ optional registry preview export
```

No decision in the sender should depend on whether registry preview export is enabled.

## Acceptance criteria before implementation

Before modifying `send_mt5_order_from_payload.py`, keep these accepted:

```text
BAT PASS
verifier PASS
external builder output is canonical reference
```

After implementation, required tests:

### 1. No flags regression

Run existing sender dry-run without registry preview flags.

Expected:

```text
same sender report/results as before
no registry preview files created
order_send_called_count=0
```

### 2. Fresh payload with preview flags

Run sender dry-run with:

```text
--registry-preview-out-csv data\r\sender_hook\registry_preview.csv
--registry-preview-out-json data\r\sender_hook\registry_preview.json
```

Expected:

```text
dry_run_check_ok_rows=1
registry_preview_rows=1
position_status=ACTIVE
strategy_key=SELL_H1H4_BEAR_AB
order_send_called_count=0
```

### 3. Blocked payload with preview flags

Run stale/blocked payload with preview flags.

Expected:

```text
BLOCKED_LOCAL_VALIDATION or BLOCKED_POSITION_POLICY
registry_preview_rows=0
no error
```

### 4. Compare with external builder

Compare sender-native preview CSV with external builder preview CSV for the same report.

Expected equivalent fields:

```text
broker_symbol
direction
lot
entry_price
sl_price
tp_price
strategy_key
strategy_alias
signal_key
order_key
position_status
```

### 5. Reconcile and policy preview

Use sender-native preview CSV with:

```text
build_gold_multi_strategy_mock_positions_from_registry.py
run_gold_multi_strategy_position_registry_reconcile_dry_run.py
run_gold_multi_strategy_registry_policy_preview_longpath.py
```

Expected:

```text
REGISTRY_ACTIVE_MATCHED=1
same_strategy_blocked_rows=1
registry_inconsistency_blocked_rows=0
```

## Recommended implementation approach

Do not rewrite sender logic.

Add a small optional export section near the end of `send_mt5_order_from_payload.py`:

```text
if registry preview output flags are provided:
    build preview rows from in-memory result rows and payload rows
    write preview CSV/JSON
```

Preferred helper functions inside sender:

```text
is_registry_preview_eligible(row, include_dry_run_check_ok=True, include_sent=False)
build_registry_preview_rows(results_df, payload_df, args, account_info)
write_registry_preview_outputs(rows, csv_path, json_path)
```

Use long-path-safe writes for preview files.

## Current recommendation

Do not implement the hook until one more stable wrapper/BAT/verifier run has passed, or until the user explicitly chooses to fold the preview hook into the sender.

For now, keep the canonical commands:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
python scripts\verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py --summary-json data\r\ff\summary.json --out-json data\r\ff\summary_verify.json --out-csv data\r\ff\summary_verify_checks.csv
```

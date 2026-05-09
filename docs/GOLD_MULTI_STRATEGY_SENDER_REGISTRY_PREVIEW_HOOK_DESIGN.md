# GOLD multi-strategy sender registry preview hook design

Last updated: 2026-05-10

## Purpose

This document defines the next safe integration step for connecting `send_mt5_order_from_payload.py` to the position registry flow.

The goal is **not** to write the production registry yet.

The goal is to add a sender-side dry-run-only registry preview hook that emits the registry row that would be written after a successful real/demo `order_send`.

Target script:

```text
scripts/send_mt5_order_from_payload.py
```

Current state:

```text
scripts/send_mt5_order_from_payload.py still supports only:
- block_any
- allow_same_direction
- allow_any_until_max
```

It does not yet support:

```text
block_same_strategy_and_opposite_direction
```

It also does not yet write:

```text
position_registry.csv
```

## Safety boundary

This hook must remain preview-only.

It must not:

```text
call mt5.order_send because of the hook
call mt5.order_check because of the hook
write production position_registry.csv
mutate existing Mochipoyo ledgers
mutate trigger-state files
modify run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
```

The existing sender behavior must remain unchanged unless the new preview CLI args are explicitly provided.

Default behavior must remain exactly as today.

## Why this hook is needed

The already validated external wrapper chain proves that registry rows can be generated from payload/send report metadata.

Validated chain so far:

```text
controlled send report with tickets
→ payload CSV extraction
→ mt5_report ticket extraction
→ registry preview row generation
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

However, the eventual production flow needs the sender to be able to prepare the row it would write after a successful order send.

The dry-run hook is an intermediate step between:

```text
external post-send-report registry preview
```

and:

```text
real sender writes production position_registry.csv after confirmed successful order_send
```

## Proposed CLI additions

Add optional arguments:

```text
--registry-preview-out-csv <path>
--registry-preview-out-json <path>
--registry-preview-position-status ACTIVE
```

Optional synthetic ticket arguments for pure dry-run preview:

```text
--registry-preview-position-ticket-start <int>
--registry-preview-order-ticket-start <int>
--registry-preview-deal-ticket-start <int>
```

Suggested defaults:

```text
--registry-preview-position-status ACTIVE
--registry-preview-position-ticket-start 990001
--registry-preview-order-ticket-start 880001
--registry-preview-deal-ticket-start 770001
```

## Important behavior rule

The hook should run only when at least one of these is provided:

```text
--registry-preview-out-csv
--registry-preview-out-json
```

If neither is provided, sender output and behavior should be unchanged.

## Preview modes

### Mode A: dry-run / no --send

When `--send` is not provided, current sender can still perform:

```text
payload validation
symbol/tick checks
position-policy checks
mt5.order_check
```

Existing sender behavior already calls `order_check` in dry-run after local guards pass.

For registry preview, the hook should build preview rows from payload rows whose sender result status is either:

```text
DRY_RUN_ORDER_CHECK_OK
```

The preview row should use synthetic ticket arguments:

```text
position_ticket = registry_preview_position_ticket_start + row_offset
order_ticket    = registry_preview_order_ticket_start + row_offset
deal_ticket     = registry_preview_deal_ticket_start + row_offset
```

This mode does not claim a real position exists.

It is only a preview of the row shape that would be written after a successful send.

### Mode B: real/demo --send with successful order_send

This is for later. Do not implement production write yet.

If `--send` is provided and `order_send_ok=True`, the preview row should use ticket metadata from the actual `order_send` result where available:

```text
order_ticket = order_send_result.order
deal_ticket = order_send_result.deal
position_ticket = position or ticket if MT5 returns one, otherwise later resolved position ticket
```

Because MT5 market order send result may not always include the final position ticket directly, the first production version should not assume final position ticket is always available from `order_send` alone.

For the dry-run preview hook, using explicit synthetic ticket fields is acceptable.

## Recommended first implementation scope

Implement only Mode A first:

```text
--send not provided
registry preview rows are generated only for DRY_RUN_ORDER_CHECK_OK rows
synthetic ticket values are used
outputs are preview CSV/JSON only
no production registry write
```

Do not implement production registry write in this step.

Do not implement new sender position policy in this step.

Do not modify the existing Mochipoyo BAT.

## Registry preview output schema

The output should use the already validated registry row shape from:

```text
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
```

Expected columns:

```text
created_at_utc
updated_at_utc
account_login
account_server
broker_symbol
symbol
position_ticket
order_ticket
deal_ticket
magic_number
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
router_strategy_slot
router_strategy_id
candidate_rank
source_payload_csv
sender_report_json
position_status
last_seen_utc
close_status
close_reason
notes
```

## Field mapping from sender payload/result

### Account fields

From initialized MT5 account info:

```text
account_login  <- account_info.login
account_server <- account_info.server
```

### Symbol fields

```text
broker_symbol <- sender broker_symbol after --symbol override resolution
symbol        <- payload symbol if present, otherwise normalized broker symbol without suffix when possible
```

For GOLD:

```text
broker_symbol=GOLD#
symbol=GOLD
```

### Ticket fields

Mode A dry-run synthetic:

```text
position_ticket <- --registry-preview-position-ticket-start + row_offset
order_ticket    <- --registry-preview-order-ticket-start + row_offset
deal_ticket     <- --registry-preview-deal-ticket-start + row_offset
```

Mode B later real/demo send:

```text
order_ticket <- order_send result order
deal_ticket  <- order_send result deal
position_ticket <- resolved MT5 position ticket, not blindly assumed unless available
```

### Trade fields

Use sender-normalized values where possible:

```text
direction   <- payload direction
lot         <- payload lot
entry_price <- current_execution_price from sender result
sl_price    <- sender rounded sl_price
tp_price    <- sender rounded tp_price
magic_number <- payload magic_number or sender default
```

### Strategy fields

Same inference already validated in registry preview builders:

```text
strategy_key <- router_strategy_slot or pair_name or strategy_id
strategy_alias <- BUY_C for BUY_C_ENV/C_ENV, SELL_AB for H1H4_BEAR/BEAR_AB, etc.
strategy_id <- payload strategy_id / router_strategy_id
condition_id <- payload condition_id or strategy_id
signal_key <- payload signal_key
order_key <- payload order_key or payload_key
payload_key <- payload payload_key or order_key
router_strategy_slot <- payload router_strategy_slot or strategy_key
router_strategy_id <- payload router_strategy_id or strategy_id
candidate_rank <- payload candidate_rank
```

### Source fields

```text
source_payload_csv <- args.input_csv
sender_report_json <- out_dir/mt5_order_send_report.json
position_status <- --registry-preview-position-status, default ACTIVE
last_seen_utc <- created_at_utc
close_status <- empty
close_reason <- empty
notes <- sender-side dry-run registry preview; no production registry mutation
```

## Output JSON summary

The JSON should include:

```text
schema_version
preview_ok
reason
input_csv
out_csv
out_json
rows_in
sender_rows_in
registry_preview_rows
send_requested
order_send_called_count
order_check_called_count if available
registry_mutated=false
ledger_mutated=false unless --send wrote order ledger through existing behavior
trigger_state_mutated=false
production_registry_mutated=false
records
```

Suggested schema version:

```text
gold_multi_strategy_sender_registry_preview_hook_v1
```

## Row selection rules

For first implementation, only include rows where:

```text
order_status == DRY_RUN_ORDER_CHECK_OK
```

Do not generate registry preview rows for:

```text
BLOCKED_PRECHECK
BLOCKED_POSITION_POLICY
BLOCKED_SYMBOL
BLOCKED_LOCAL_VALIDATION
BLOCKED_ORDER_CHECK
ERROR_ORDER_SEND
```

For later production preview mode, include rows where:

```text
order_status == SENT
order_send_ok == true
```

## Long path handling

Because this repo runs under a deep MT5/MQL5/Files path, all new registry preview output writers should use:

```text
windows_long_path(path)
```

Specifically:

```text
Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
Path(windows_long_path(path)).write_text(...)
df.to_csv(windows_long_path(path), ...)
```

Do not use plain `path.write_text(...)` for deep output paths.

## Interaction with existing sender ledger

Do not change existing ledger behavior in this step.

Existing sender writes the order ledger only when:

```text
--send is provided
```

The registry preview hook should not write to the order ledger.

If `--send` is not provided, then:

```text
order ledger should remain unchanged
registry preview CSV/JSON may be written if requested
```

## Interaction with position policy

Do not add `block_same_strategy_and_opposite_direction` to the real sender in this step.

The dry-run registry preview hook should work with existing sender policy modes:

```text
block_any
allow_same_direction
allow_any_until_max
```

Recommended validation should use a controlled payload and `block_any` with no existing position when testing `DRY_RUN_ORDER_CHECK_OK`, or use isolated/mock wrappers outside sender if real MT5 state would block.

## Validation plan

### Test 1: no preview args

Command uses sender as before.

Expected:

```text
No registry preview CSV/JSON created.
Existing mt5_order_send_report.json behavior unchanged.
```

### Test 2: preview args with no eligible rows

Use payload that fails local validation or position policy.

Expected:

```text
preview_ok=true
registry_preview_rows=0
reason=NO_ELIGIBLE_SENDER_ROWS
order_send_called_count=0 when --send absent
production_registry_mutated=false
```

### Test 3: preview args with DRY_RUN_ORDER_CHECK_OK row

Use a payload that passes sender dry-run order_check.

Expected:

```text
preview_ok=true
registry_preview_rows=1
position_ticket uses synthetic start
order_ticket uses synthetic start
deal_ticket uses synthetic start
source_payload_csv=args.input_csv
sender_report_json=out_dir/mt5_order_send_report.json
production_registry_mutated=false
```

### Test 4: feed generated preview row into reconcile/policy preview

Use generated registry preview CSV as input to:

```text
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
```

Expected:

```text
registry row schema compatible
reconcile can read it
policy preview can use it
```

## Explicit non-goals

Do not do these in this step:

```text
Do not add real production registry writes.
Do not add block_same_strategy_and_opposite_direction to sender.
Do not alter existing Mochipoyo BAT.
Do not execute close intent in MT5.
Do not integrate BTC into this sender path yet.
Do not change BUY/SELL signal generation logic.
```

## Recommended next implementation step

After this design doc:

```text
Add the dry-run-only registry preview hook to send_mt5_order_from_payload.py.
```

Keep it disabled unless preview output args are provided.

After implementation, run only dry-run validations first.

Do not use `--send` for the first validation of this hook.

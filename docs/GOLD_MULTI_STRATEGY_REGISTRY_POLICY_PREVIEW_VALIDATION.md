# GOLD multi-strategy registry policy preview validation

Last updated: 2026-05-09

## Purpose

This document records validation results for the registry-aware policy preview layer.

The purpose of this layer is to combine:

```text
order_payloads.csv candidate
+ current positions snapshot/mock CSV
+ position_registry.csv ownership metadata
+ optional order ledger duplicate keys
```

and produce sender-like ALLOW/BLOCK decisions before modifying the real sender.

The real sender remains unchanged.

```text
scripts/send_mt5_order_from_payload.py: not modified
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat: not modified
existing Mochipoyo ledger files: not modified
existing trigger-state files: not modified
```

## Safety boundary

The preview layer is non-executing and read-only.

```text
No MetaTrader5 import.
No mt5.order_check.
No mt5.order_send.
No registry mutation.
No Mochipoyo ledger mutation.
No trigger-state mutation.
No close-position execution.
```

Validated safety counters:

```text
mt5_imported: false
order_check_called_count: 0
order_send_called_count: 0
registry_mutated: false
ledger_mutated: false
trigger_state_mutated: false
```

## Implemented script

```text
scripts/run_gold_multi_strategy_registry_policy_preview.py
```

Commit:

```text
5e7f3bb05d68940c866c40db3cafd8c4318c0136
```

Primary outputs:

```text
data/research_results/gold_multi_strategy_position_registry/registry_policy_preview.csv
data/research_results/gold_multi_strategy_position_registry/registry_policy_preview.json
data/research_results/gold_multi_strategy_position_registry/registry_policy_preview_reconcile.csv
```

## Policy preview rules

Policy name:

```text
block_same_strategy_and_opposite_direction
```

Rules:

```text
1. Invalid payload => BLOCK
2. same signal_key / order_key duplicate => BLOCK
3. registry inconsistency => BLOCK by default
4. same strategy already has an ACTIVE matched registry position => BLOCK
5. same symbol opposite direction exists in current positions => BLOCK
6. total open positions >= max_total_positions => BLOCK
7. requested lot > max_lot_per_order => BLOCK
8. otherwise => ALLOW
```

Default caps:

```text
max_total_positions: 5
max_lot_per_order: 0.02
```

## Test inputs

### Payload

Controlled payload:

```text
data/research_results/gold_multi_strategy_position_policy_preflight/order_payloads_policy_test_same_direction_buy.csv
```

Payload row:

```text
requested_strategy_key=BUY_C_ENV_RR2_72H
requested_symbol=GOLD#
requested_direction=BUY
requested_lot=0.01
```

### Positions snapshot

Mock positions CSV:

```text
data/research_results/gold_multi_strategy_position_policy_preflight/mock_positions_same_strategy_buy_c.csv
```

Mock position:

```text
ticket=990001
symbol=GOLD#
direction=BUY
volume=0.01
magic=26050601
comment=ms BUY_C BUY_C_ENV_RR2_72H
external_id=BUY_C_ENV_RR2_72H|MOCK
```

## Validation case 1: same strategy blocked by ACTIVE matched registry

### Registry input

```text
data/research_results/gold_multi_strategy_position_registry/position_registry_test_active_buy_c_ticket_990001.csv
```

Registry row:

```text
position_ticket=990001
broker_symbol=GOLD#
direction=BUY
lot=0.01
strategy_key=BUY_C_ENV_RR2_72H
position_status=ACTIVE
```

### Command

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_test_active_buy_c_ticket_990001.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD# --max-total-positions 5 --max-lot-per-order 0.02
```

### Observed summary

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

### Observed row

```text
requested_strategy_key=BUY_C_ENV_RR2_72H
requested_symbol=GOLD#
requested_direction=BUY
requested_lot=0.01
existing_total_positions=1
existing_symbol_positions=1
existing_symbol_directions=BUY
registry_matched_rows=1
registry_missing_position_rows=0
unregistered_position_rows=0
same_strategy_blocked=true
registry_inconsistency_blocked=false
final_policy_decision=BLOCK
```

Reason:

```text
same_strategy: ACTIVE matched registry position already exists for strategy=BUY_C_ENV_RR2_72H; tickets=['990001']
```

Decision:

```text
PASS.
```

Interpretation:

```text
The preview layer correctly uses registry ownership, not only MT5/comment text,
to block another entry from the same strategy when an ACTIVE matched registry position exists.
```

## Validation case 2: registry inconsistency blocked by default

### Registry input

```text
data/research_results/gold_multi_strategy_position_registry/position_registry_test_missing_mt5_buy_c_ticket_999999.csv
```

Registry row:

```text
position_ticket=999999
broker_symbol=GOLD#
direction=BUY
lot=0.01
strategy_key=BUY_C_ENV_RR2_72H
position_status=ACTIVE
```

Current positions still contain:

```text
position_ticket=990001
symbol=GOLD#
direction=BUY
volume=0.01
```

### Command

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_test_missing_mt5_buy_c_ticket_999999.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD# --max-total-positions 5 --max-lot-per-order 0.02
```

### Observed summary

```text
preview_ok: true
reason: POLICY_PREVIEW_EVALUATED
rows_in: 1
rows_out: 1
allow_rows: 0
blocked_rows: 1
same_strategy_blocked_rows: 0
opposite_direction_blocked_rows: 0
total_position_cap_blocked_rows: 0
per_order_lot_blocked_rows: 0
duplicate_key_blocked_rows: 0
registry_inconsistency_blocked_rows: 1
reconcile_status_counts:
  REGISTRY_ACTIVE_MISSING_POSITION: 1
  POSITION_WITHOUT_ACTIVE_REGISTRY: 1
```

### Observed row

```text
requested_strategy_key=BUY_C_ENV_RR2_72H
requested_symbol=GOLD#
requested_direction=BUY
requested_lot=0.01
existing_total_positions=1
existing_symbol_positions=1
existing_symbol_directions=BUY
registry_matched_rows=0
registry_missing_position_rows=1
unregistered_position_rows=1
same_strategy_blocked=false
registry_inconsistency_blocked=true
final_policy_decision=BLOCK
```

Reason:

```text
registry_inconsistency: registry has ACTIVE row(s) missing from current positions: count=1
```

Decision:

```text
PASS.
```

Interpretation:

```text
The preview layer correctly blocks new sends when registry ownership state is inconsistent.
This is the desired initial safety behavior before any automatic registry cleanup is introduced.
```

## Validation matrix

Current registry policy preview validation state:

```text
ACTIVE matched same-strategy registry position blocks new same-strategy payload: PASS
Registry ACTIVE missing-position inconsistency blocks new payload by default: PASS
Unregistered current position is surfaced through reconciliation output: PASS
Read-only safety counters: PASS
```

## Design implications

The preview layer now bridges the gap between pure reconciliation and future sender policy integration.

The future sender can use the same conceptual ordering:

```text
1. account guard
2. payload local validation
3. duplicate order_key / signal_key
4. registry reconciliation
5. registry inconsistency safety block
6. same strategy max 1 via ACTIVE matched registry rows
7. same symbol opposite direction via current positions
8. total account positions max 5
9. per-order lot max 0.02
10. symbol info / volume step / price sanity
11. order_check
12. order_send only if --send
13. registry write only after confirmed successful send
```

## Important note about registry writes

This preview does not write or update `position_registry.csv`.

Future registry writing must be implemented separately and only after a confirmed successful send result.

Recommended first sender-adjacent implementation remains dry-run only:

```text
simulate registry row creation from payload + synthetic send result
write to a test registry path only
never write to production registry until demo send flow is explicitly approved
```

## Recommended next step

Do not modify the real sender yet.

Next safe step:

```text
Create a registry write preview / simulated-send registry row builder.
```

Suggested script:

```text
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
```

Purpose:

```text
Take a payload row and a synthetic successful send result,
produce the exact position_registry.csv row that would be written after a real successful order_send,
but write only to a preview/test registry path.
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

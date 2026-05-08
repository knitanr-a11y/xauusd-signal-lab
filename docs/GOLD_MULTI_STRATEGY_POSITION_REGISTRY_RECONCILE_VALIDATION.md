# GOLD multi-strategy position registry reconciliation validation

Last updated: 2026-05-09

## Purpose

This document records validation results for the isolated `position_registry.csv` dry-run / reconciliation layer.

The purpose of this layer is to validate position ownership semantics before modifying the real MT5 sender.

The sender is still unchanged.

```text
scripts/send_mt5_order_from_payload.py: not modified
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat: not modified
existing Mochipoyo ledger files: not modified
existing trigger-state files: not modified
```

## Safety boundary

The registry reconciliation layer is read-only / report-only.

```text
No mt5.order_send.
No mt5.order_check.
No registry mutation.
No existing Mochipoyo ledger mutation.
No trigger-state mutation.
No close-position execution.
```

The current reconciliation script can read either controlled mock position CSVs or real MT5 positions, but the validations in this document used mock/snapshot CSV input.

## Implemented scripts

### Mock positions builder

```text
scripts/build_gold_multi_strategy_mock_positions.py
```

Used scenario:

```text
same_strategy_buy_c
```

Output:

```text
data/research_results/gold_multi_strategy_position_policy_preflight/mock_positions_same_strategy_buy_c.csv
```

Mock position created:

```text
ticket=990001
symbol=GOLD#
direction=BUY
volume=0.01
magic=26050601
comment=ms BUY_C BUY_C_ENV_RR2_72H
external_id=BUY_C_ENV_RR2_72H|MOCK
```

Safety output:

```text
mt5_imported: false
order_check_called: false
order_send_called: false
ledger_written: false
```

### Position registry test data builder

```text
scripts/build_gold_multi_strategy_position_registry_test_data.py
```

Validated scenarios:

```text
active_buy_c_ticket_990001
missing_mt5_buy_c_ticket_999999
empty
```

Safety output:

```text
mt5_imported: false
order_check_called: false
order_send_called: false
ledger_written: false
trigger_state_written: false
```

### Position registry reconciliation dry-run

```text
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
```

Primary outputs:

```text
data/research_results/gold_multi_strategy_position_registry/position_registry_reconcile_dry_run.csv
data/research_results/gold_multi_strategy_position_registry/position_registry_reconcile_dry_run.json
data/research_results/gold_multi_strategy_position_registry/position_registry_reconcile_positions_snapshot.csv
```

Validated safety output:

```text
order_send_called_count: 0
order_check_called_count: 0
registry_mutated: false
ledger_mutated: false
trigger_state_mutated: false
```

## Validation case 1: ACTIVE registry row matched current position

### Build mock position

```cmd
python scripts\build_gold_multi_strategy_mock_positions.py --scenario same_strategy_buy_c --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --broker-symbol GOLD#
```

### Build registry row

```cmd
python scripts\build_gold_multi_strategy_position_registry_test_data.py --scenario active_buy_c_ticket_990001 --out-dir data\research_results\gold_multi_strategy_position_registry --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3"
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

### Reconcile

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_test_active_buy_c_ticket_990001.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD#
```

Observed:

```text
reconcile_ok: true
registry_status: REGISTRY_READ_OK
registry_rows: 1
active_registry_rows: 1
positions_rows: 1
reconcile_rows: 1
matched_active_registry_rows: 1
matched_with_mismatch_rows: 0
missing_position_rows: 0
unregistered_position_rows: 0
status_counts: REGISTRY_ACTIVE_MATCHED=1
```

Row result:

```text
row_type: ACTIVE_REGISTRY_ROW
registry_position_ticket: 990001
registry_strategy_key: BUY_C_ENV_RR2_72H
position_ticket: 990001
position_symbol: GOLD#
position_direction: BUY
position_lot: 0.01
ticket_match: true
symbol_match: true
direction_match: true
lot_match: true
strategy_detected_in_position: true
reconcile_status: REGISTRY_ACTIVE_MATCHED
reconcile_reason: active registry row matched current open position
```

Decision:

```text
PASS.
```

## Validation case 2: ACTIVE registry row missing from current positions

### Build registry row

```cmd
python scripts\build_gold_multi_strategy_position_registry_test_data.py --scenario missing_mt5_buy_c_ticket_999999 --out-dir data\research_results\gold_multi_strategy_position_registry --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3"
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

### Reconcile

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_test_missing_mt5_buy_c_ticket_999999.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD#
```

Observed:

```text
reconcile_ok: true
registry_status: REGISTRY_READ_OK
registry_rows: 1
active_registry_rows: 1
positions_rows: 1
reconcile_rows: 2
matched_active_registry_rows: 0
matched_with_mismatch_rows: 0
missing_position_rows: 1
unregistered_position_rows: 1
status_counts:
  REGISTRY_ACTIVE_MISSING_POSITION=1
  POSITION_WITHOUT_ACTIVE_REGISTRY=1
```

Rows:

```text
ACTIVE_REGISTRY_ROW:
  registry_position_ticket=999999
  reconcile_status=REGISTRY_ACTIVE_MISSING_POSITION
  reconcile_reason=active registry ticket not found in current positions: ticket=999999

POSITION_WITHOUT_ACTIVE_REGISTRY:
  position_ticket=990001
  position_symbol=GOLD#
  position_direction=BUY
  position_lot=0.01
  reconcile_status=POSITION_WITHOUT_ACTIVE_REGISTRY
  reconcile_reason=current position ticket is not present in ACTIVE registry rows: ticket=990001
```

Decision:

```text
PASS.
```

Interpretation:

```text
The dry-run correctly detects both sides of the inconsistency:
1. registry says ticket 999999 should be active, but it is missing from positions
2. current position ticket 990001 exists, but no ACTIVE registry row owns it
```

## Validation case 3: empty registry with current position

### Build empty registry

```cmd
python scripts\build_gold_multi_strategy_position_registry_test_data.py --scenario empty --out-dir data\research_results\gold_multi_strategy_position_registry --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3"
```

### Reconcile

```cmd
python scripts\run_gold_multi_strategy_position_registry_reconcile_dry_run.py --registry-csv data\research_results\gold_multi_strategy_position_registry\position_registry_test_empty.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_position_registry --symbol GOLD#
```

Observed:

```text
reconcile_ok: true
registry_status: REGISTRY_EMPTY
registry_rows: 0
active_registry_rows: 0
positions_rows: 1
reconcile_rows: 1
matched_active_registry_rows: 0
matched_with_mismatch_rows: 0
missing_position_rows: 0
unregistered_position_rows: 1
status_counts: POSITION_WITHOUT_ACTIVE_REGISTRY=1
```

Row:

```text
POSITION_WITHOUT_ACTIVE_REGISTRY:
  position_ticket=990001
  position_symbol=GOLD#
  position_direction=BUY
  position_lot=0.01
  reconcile_status=POSITION_WITHOUT_ACTIVE_REGISTRY
  reconcile_reason=current position ticket is not present in ACTIVE registry rows: ticket=990001
```

Decision:

```text
PASS.
```

## Validation matrix

Current registry reconciliation validation state:

```text
ACTIVE registry row matched current position: PASS
ACTIVE registry row missing from current positions: PASS
Current position without ACTIVE registry row: PASS
Empty registry with current position: PASS
Read-only safety counters: PASS
```

## Design implications

The registry dry-run layer can now identify the ownership state needed by the future sender policy:

```text
REGISTRY_ACTIVE_MATCHED
REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH
REGISTRY_ACTIVE_MISSING_POSITION
POSITION_WITHOUT_ACTIVE_REGISTRY
```

For future sender integration, the recommended interpretation is:

```text
REGISTRY_ACTIVE_MATCHED:
  Treat as valid owned open position.
  Can be used for same_strategy max 1 checks.

REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH:
  Treat as unsafe.
  Block new sends until inspected.

REGISTRY_ACTIVE_MISSING_POSITION:
  Registry cleanup/reconciliation is required.
  Do not blindly count it as open forever, but do not mutate automatically in the first implementation.

POSITION_WITHOUT_ACTIVE_REGISTRY:
  Treat as unmanaged existing position.
  For same-symbol direction conflict and total position cap, still count it.
  For same_strategy ownership, do not assume strategy unless a safe mapping exists.
```

## Recommended next step

Do not modify the real sender yet.

Next safe implementation step:

```text
Add an isolated registry policy preview that combines:
1. current payload candidate
2. current positions snapshot
3. position_registry reconciliation output

and produces a sender-like decision without calling order_check/order_send.
```

This can become the bridge between pure reconciliation and real sender policy integration.

Suggested future script name:

```text
scripts/run_gold_multi_strategy_registry_policy_preview.py
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```

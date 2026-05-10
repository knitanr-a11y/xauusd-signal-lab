# GOLD multi-strategy fresh sender registry policy full-cycle validation

Last updated: 2026-05-10

## Purpose

This document records validation for the one-command full-cycle wrapper, its dry-run BAT, and its read-only verifier:

```text
scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle.py
scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
scripts/verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py
```

Validated chain:

```text
fresh MT5 tick-based payload
→ send_mt5_order_from_payload.py dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender registry preview row
→ registry-derived mock position
→ exact registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
→ read-only summary verification
```

## Safety boundary

```text
No --send was passed.
No real mt5.order_send was called.
No production position_registry.csv was written.
No existing Mochipoyo ledger was mutated.
No trigger-state file was mutated.
No existing Mochipoyo BAT was modified.
```

The wrapper does call the real sender in dry-run mode only.

The fresh payload builder reads MT5 account/symbol/tick metadata.

The real sender dry-run may call `mt5.order_check`, but never `mt5.order_send` because `--send` is not passed.

The verifier is read-only and does not import MT5.

## Implementation note: short work paths

During the first full-cycle attempt, the wrapper failed because `send_mt5_order_from_payload.py` still uses plain `Path.mkdir()` for its output directory and hit Windows path length error `WinError 206` under a deep MT5/MQL5/Files path.

The full-cycle wrapper was updated to use short internal directories:

```text
f  = fresh payload work dir
c  = sender dry-run registry preview cycle dir
r  = reconcile dir
p  = policy preview dir
mp.csv = mock positions CSV
summary.json = full-cycle summary JSON
```

Validated short top-level output:

```text
data/r/ff
```

Implementation commit:

```text
aba2c061b41a67c0d027a573d88708b8c3449666
```

## Validated Python command

```cmd
python scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle.py --out-dir data\r\ff --broker-symbol GOLD# --symbol GOLD --direction SELL --lot 0.01 --sl-distance 10 --tp-distance 20 --expected-login 75539039 --require-demo-account --select-symbol --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05 --max-total-positions 5 --max-lot-per-order 0.02
```

## Observed top-level result

```text
cycle_ok=true
reason=FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS
schema_version=gold_multi_strategy_fresh_sender_registry_policy_full_cycle_v1
send_requested=false
```

Output summary:

```text
summary_json=data/r/ff/summary.json
```

Decision:

```text
PASS.
```

## Step result table

Observed:

```text
build_fresh_sender_valid_payload: true / returncode 0
sender_dry_run_registry_preview_cycle: true / returncode 0
build_mock_positions_from_registry: true / returncode 0
reconcile_registry_with_mock_positions: true / returncode 0
registry_policy_preview: true / returncode 0
```

Decision:

```text
PASS.
```

## Fresh payload result

Observed:

```text
build_ok=true
reason=FRESH_SENDER_VALID_PAYLOAD_BUILT
rows_out=1
```

Observed price metadata:

```text
bid=4715.02
ask=4715.97
digits=2
entry=4715.02
sl=4725.02
tp=4695.02
validation_errors=[]
```

Generated order key from one Python run:

```text
FRESH_SENDER_VALID|SELL_H1H4_BEAR_AB|GOLD|SELL|B_ONLY_SAFE|20260510T002755Z|MOCHIPOYO_PAYLOAD
```

Decision:

```text
PASS.
```

## Sender dry-run registry preview cycle result

Observed:

```text
cycle_ok=true
reason=SENDER_DRY_RUN_REGISTRY_PREVIEW_EVALUATED
registry_preview_reason=REGISTRY_PREVIEW_ROWS_BUILT
registry_preview_rows=1
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

Decision:

```text
PASS.
```

## Mock positions result

Observed:

```text
build_ok=true
reason=MOCK_POSITIONS_BUILT_FROM_REGISTRY
rows_out=1
```

Mock positions CSV:

```text
data/r/ff/mp.csv
```

Decision:

```text
PASS.
```

## Exact reconcile result

Observed:

```text
reconcile_ok=true
reason=RECONCILE_EVALUATED
matched_active_registry_rows=1
matched_with_mismatch_rows=0
missing_position_rows=0
unregistered_position_rows=0
status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Decision:

```text
PASS.
```

## Registry-aware policy preview result

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
registry_inconsistency_blocked_rows=0
reconcile_status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Final policy implication:

```text
same_strategy BLOCK confirmed for SELL_H1H4_BEAR_AB with ACTIVE matched registry position.
```

Decision:

```text
PASS.
```

## Safety result

Observed:

```text
wrapper_passed_send_flag=false
send_requested=false
order_send_called_count=0
production_registry_mutated=false
trigger_state_mutated=false
existing_sender_modified=false
existing_bat_modified=false
```

Decision:

```text
PASS.
```

## Dry-run BAT validation

New BAT:

```text
scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
```

Implementation commit:

```text
05d3c4d6eb2b6cf789e944072cb44f00775fde8d
```

Command:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
```

Observed top-level result:

```text
cycle_ok=true
reason=FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS
summary_json=data/r/ff/summary.json
exit code=0
```

Observed fresh payload from BAT run:

```text
build_ok=true
reason=FRESH_SENDER_VALID_PAYLOAD_BUILT
rows_out=1
bid=4715.02
ask=4715.97
entry=4715.02
sl=4725.02
tp=4695.02
validation_errors=[]
```

Generated BAT-run order key:

```text
FRESH_SENDER_VALID|SELL_H1H4_BEAR_AB|GOLD|SELL|B_ONLY_SAFE|20260510T003233Z|MOCHIPOYO_PAYLOAD
```

Observed sender cycle:

```text
cycle_ok=true
reason=SENDER_DRY_RUN_REGISTRY_PREVIEW_EVALUATED
registry_preview_reason=REGISTRY_PREVIEW_ROWS_BUILT
registry_preview_rows=1
sender_metrics:
  rows_in=1
  rows_out=1
  dry_run_check_ok_rows=1
  sent_rows=0
  blocked_position_policy_rows=0
  error_rows=0
  order_send_called_count=0
```

Observed mock positions:

```text
build_ok=true
reason=MOCK_POSITIONS_BUILT_FROM_REGISTRY
rows_out=1
```

Observed reconcile:

```text
reconcile_ok=true
reason=RECONCILE_EVALUATED
matched_active_registry_rows=1
matched_with_mismatch_rows=0
missing_position_rows=0
unregistered_position_rows=0
status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
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
registry_inconsistency_blocked_rows=0
reconcile_status_counts:
  REGISTRY_ACTIVE_MATCHED: 1
```

Step table:

```text
build_fresh_sender_valid_payload: true / returncode 0
sender_dry_run_registry_preview_cycle: true / returncode 0
build_mock_positions_from_registry: true / returncode 0
reconcile_registry_with_mock_positions: true / returncode 0
registry_policy_preview: true / returncode 0
```

Safety:

```text
send_requested=false
wrapper_passed_send_flag=false
order_send_called_count=0
production_registry_mutated=false
trigger_state_mutated=false
existing_sender_modified=false
existing_bat_modified=false
```

Decision:

```text
PASS.
```

## Read-only summary verifier validation

New verifier:

```text
scripts/verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py
```

Implementation commit:

```text
2620a396927fbb15e76700dd2a329c6d8b8b4dd8
```

Command:

```cmd
python scripts\verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py --summary-json data\r\ff\summary.json --out-json data\r\ff\summary_verify.json --out-csv data\r\ff\summary_verify_checks.csv
```

Observed result:

```text
verify_ok=true
reason=SUMMARY_VERIFY_PASS
checks_total=26
checks_failed=0
failed_check_names=[]
```

Verified key checks:

```text
cycle_ok=true
reason=FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS
send_requested=false
safety.wrapper_passed_send_flag=false
safety.production_registry_mutated=false
safety.trigger_state_mutated=false
safety.existing_sender_modified=false
safety.existing_bat_modified=false
sender_cycle.cycle_ok=true
sender_cycle.sender_metrics.dry_run_check_ok_rows=1
sender_cycle.sender_metrics.order_send_called_count=0
sender_cycle.sender_metrics.sent_rows=0
sender_cycle.sender_metrics.error_rows=0
sender_cycle.registry_preview_rows=1
mock_positions.build_ok=true
mock_positions.rows_out=1
reconcile.reconcile_ok=true
reconcile.matched_active_registry_rows=1
reconcile.matched_with_mismatch_rows=0
reconcile.missing_position_rows=0
reconcile.unregistered_position_rows=0
policy_preview.preview_ok=true
policy_preview.same_strategy_blocked_rows=1
policy_preview.registry_inconsistency_blocked_rows=0
policy_preview.allow_rows=0
policy_preview.blocked_rows=1
```

Verifier safety:

```text
read_only=true
mt5_imported=false
order_check_called=false
order_send_called=false
ledger_mutated=false
registry_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## Current implication

The following can now be reproduced with one BAT command and verified with one read-only verifier command:

```text
fresh MT5 tick payload
→ real sender dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ registry preview row
→ registry-derived mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
→ read-only summary verification
```

Canonical dry-run command:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
```

Canonical verifier command:

```cmd
python scripts\verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py --summary-json data\r\ff\summary.json --out-json data\r\ff\summary_verify.json --out-csv data\r\ff\summary_verify_checks.csv
```

This full-cycle wrapper/BAT/verifier set is now the safest next integration layer before modifying the real sender or writing production registry.

## Recommended next step

Do not write production registry yet.

Recommended next step:

```text
Use the BAT + verifier pair above as the canonical dry-run validation commands for the sender/registry/policy path.
```

After another stable round, decide whether to:

```text
A. keep wrapper/BAT/verifier-only integration for demo dry-run validation, or
B. add disabled-by-default registry preview flags directly to send_mt5_order_from_payload.py.
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

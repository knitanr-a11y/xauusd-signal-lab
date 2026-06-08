# GOLD V2 25C62 CoreB G1 A002 fixed dry-run direction package audit spec

Date: 2026-06-08

Step: `25C62_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY`

Mode: integrated audit-only human-direction package

## Purpose

25C62 reads the 25C61 fixed-condition minimal gate audit and creates one consolidated human-direction package. It keeps A002 and the retained filters fixed and reduces the next human decision to the smallest explicit scope needed for a later audit-only dry-run branch.

This step is not execution and must not change signal conditions.

## Required inputs

From:

```text
FX_OUTPUTS/gold_v2_25c61_coreb_g1_a002_fixed_dry_run_minimal_gate_integrated_audit_only/
```

Required files:

```text
02_25c61_a002_fixed_dry_run_minimal_gate_integrated_audit_summary.json
04_25c61_contract_audit.csv
05_25c61_condition_freeze_matrix.csv
06_25c61_minimal_gate_matrix.csv
07_25c61_fixed_condition_next_decision_matrix.csv
08_25c61_execution_boundary_matrix.csv
09_25c61_next_step_plan.csv
10_25c61_handoff_notes.csv
```

## Source-of-truth facts from 25C61

25C62 must preserve these facts:

```text
step = 25C61_COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_ONLY
status = COREB_G1_A002_FIXED_DRY_RUN_MINIMAL_GATE_INTEGRATED_AUDIT_READY_AUDIT_ONLY_EXECUTION_BLOCKED_MINIMAL_GATES_IDENTIFIED
audit_only = true
representative_variant_code = A002
representative_filters = same_count>=2&unique_origins>=2, unique_origins>=2
condition_changed = false
source_recovery_executed = false
source_mutation_executed = false
minimal_gate_rows = 5
minimal_gates_blocking_future_dry_run = 5
source_confirmed_for_execution = false
a002_variant_approved = false
human_dry_run_execution_approval = false
execution_gate_open = false
future_dry_run_execution_allowed = false
next_recommended_step = WAIT_FOR_EXPLICIT_HUMAN_DIRECTION_FOR_FIXED_CONDITION_AUDIT_ONLY
total_stop_rows = 0
```

All execution and external flags in 25C61 must remain false.

## Direction package requirement

25C62 must consolidate the 25C61 minimal gates into three human-direction items:

```text
1. confirm_existing_bound_source_for_audit_only_dry_run_without_source_recovery
2. approve_A002_fixed_filters_for_audit_only_dry_run
3. permit_fixed_condition_audit_only_dry_run_execution_without_live_or_external_actions
```

The two remaining gates are derived and must stay false in 25C62:

```text
execution_gate_open = false
future_dry_run_execution_allowed = false
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only/
```

Expected files:

```text
00_不要_25c62_file_request_list.csv
01_25c62_GOLD_V2_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY_REPORT.md
02_25c62_a002_fixed_dry_run_direction_package_summary.json
03_25c62_input_audit.csv
04_25c62_contract_audit.csv
05_25c62_fixed_condition_scope_matrix.csv
06_25c62_human_direction_required_matrix.csv
07_25c62_derived_gate_matrix.csv
08_25c62_execution_boundary_matrix.csv
09_25c62_next_step_plan.csv
10_25c62_handoff_notes.csv
```

## Success status

```text
COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_READY_AUDIT_ONLY_HUMAN_DIRECTION_REQUIRED_NO_EXECUTION
```

## Stop statuses

```text
25C62_STOP_MISSING_INPUT_AUDIT_ONLY
25C62_STOP_25C61_CONTRACT_UNSAFE_AUDIT_ONLY
25C62_STOP_FIXED_CONDITION_SCOPE_UNSAFE_AUDIT_ONLY
```

## Next recommended step

25C62 recommends waiting for a single explicit human direction. It must not recommend execution automatically.

```text
WAIT_FOR_SINGLE_FIXED_CONDITION_DRY_RUN_DIRECTION_AUDIT_ONLY
```

## Boundaries

25C62 must not record acceptance, open the execution gate, approve variants, execute replay or dry-run, mutate sources or conditions, confirm source for execution, unblock live evaluator, send Discord notifications, place MT5 orders, call AI API, run live hooks, or create final signals.

NO_SIGNAL Discord notification remains disabled.

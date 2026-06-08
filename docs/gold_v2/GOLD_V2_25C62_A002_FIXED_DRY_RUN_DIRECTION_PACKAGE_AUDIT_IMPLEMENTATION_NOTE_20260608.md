# GOLD V2 25C62 A002 fixed dry-run direction package audit implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
25C62_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY
```

Mode: integrated audit-only human-direction package.

## What was implemented

Added a repository-backed audit-only Python script and BAT launcher for 25C62.

```text
scripts/gold_v2_runtime/audit_gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only.py
scripts/gold_v2_runtime/bat/25C62_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY.bat
```

The BAT keeps the command window open with `pause` on both success and STOP/error paths.

## Input files

25C62 reads from:

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

## Output directory

```text
FX_OUTPUTS/gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only/
```

Expected outputs:

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

## Expected result

25C62 keeps A002 and filters fixed and consolidates five minimal gates into three human-direction items:

```text
confirm_existing_bound_source_for_audit_only_dry_run_without_source_recovery
approve_A002_fixed_filters_for_audit_only_dry_run
permit_fixed_condition_audit_only_dry_run_execution_without_live_or_external_actions
```

Expected summary:

```text
human_direction_required_rows = 3
derived_gate_rows = 2
condition_changed = false
future_dry_run_execution_allowed = false
dry_run_executed = false
```

## Success status

```text
COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_READY_AUDIT_ONLY_HUMAN_DIRECTION_REQUIRED_NO_EXECUTION
```

## Stop conditions

```text
25C62_STOP_MISSING_INPUT_AUDIT_ONLY
25C62_STOP_25C61_CONTRACT_UNSAFE_AUDIT_ONLY
25C62_STOP_FIXED_CONDITION_SCOPE_UNSAFE_AUDIT_ONLY
```

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C62_COREB_G1_A002_FIXED_DRY_RUN_DIRECTION_PACKAGE_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c62_coreb_g1_a002_fixed_dry_run_direction_package_audit_only.py
```

## Next step

25C62 recommends no automatic execution. It records:

```text
WAIT_FOR_SINGLE_FIXED_CONDITION_DRY_RUN_DIRECTION_AUDIT_ONLY
```

## Explicit boundaries

25C62 does not change signal conditions, filters, thresholds, or sources. It does not record acceptance, open the execution gate, approve A002/A004 or any variant, execute replay, execute dry-run, recover sources, run live paths, call AI API, notify Discord, place MT5 orders, run live hooks, or create final signals.

NO_SIGNAL Discord notification remains disabled.

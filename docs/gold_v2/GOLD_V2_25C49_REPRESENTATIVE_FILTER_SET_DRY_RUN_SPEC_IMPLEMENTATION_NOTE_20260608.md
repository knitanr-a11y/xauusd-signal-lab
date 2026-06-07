# GOLD V2 25C49 representative filter set dry-run spec implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY
```

Mode: audit-only dry-run specification package.

## What was implemented

Added a repository-backed audit-only Python script and BAT launcher for 25C49.

```text
scripts/gold_v2_runtime/audit_gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only.py
scripts/gold_v2_runtime/bat/25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY.bat
```

The BAT keeps the command window open with `pause` on both success and STOP/error paths.

## Input files

25C49 reads from:

```text
FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/
```

Required files:

```text
02_25c48_representative_filter_set_review_spec_summary.json
04_25c48_contract_audit.csv
05_25c48_representative_filter_set.csv
06_25c48_review_spec_matrix.csv
07_25c48_blocked_execution_matrix.csv
08_25c48_gates.csv
09_25c48_next_step_plan.csv
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/
```

Expected outputs:

```text
00_不要_25c49_file_request_list.csv
01_25c49_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY_REPORT.md
02_25c49_representative_filter_set_dry_run_spec_summary.json
03_25c49_input_audit.csv
04_25c49_contract_audit.csv
05_25c49_dry_run_input_contract.csv
06_25c49_dry_run_output_contract.csv
07_25c49_dry_run_acceptance_matrix.csv
08_25c49_blocked_execution_matrix.csv
09_25c49_next_step_plan.csv
10_25c49_handoff_notes.csv
```

## Source-of-truth facts

25C49 preserves the 25C48 representative facts:

```text
representative_variant_code = A002
representative_retention_priority_cutoff = 1
representative_total_unique_damage_keys = 69
representative_covered_unique_keys = 69
representative_open_unique_keys = 0
representative_retained_filter_count = 2
representative_filters = same_count>=2&unique_origins>=2, unique_origins>=2
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
```

## What 25C49 writes

25C49 writes the future dry-run package contract only:

```text
dry-run input contract
dry-run output contract
dry-run acceptance matrix
blocked execution matrix
next step plan
handoff notes
```

## Success conditions

25C49 succeeds only when:

```text
required 25C48 files exist
25C48 summary status and next step match the expected contract
25C48 representative filter set exactly matches the two expected filters
25C48 matrices have no STOP rows
all execution and external flags remain false
future dry-run remains blocked in 25C49
```

Successful status:

```text
COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_READY_AUDIT_ONLY
```

## Stop conditions

```text
25C49_STOP_MISSING_INPUT_AUDIT_ONLY
25C49_STOP_25C48_CONTRACT_UNSAFE_AUDIT_ONLY
25C49_STOP_DRY_RUN_SPEC_UNSAFE_AUDIT_ONLY
```

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only.py
```

## Next step

25C49 may recommend only this next audit-only readiness review step:

```text
25C50_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY
```

25C50 must remain audit-only unless a later explicit instruction changes the boundary.

## Explicit boundaries

25C49 does not approve A002/A004 or any variant.

25C49 does not execute replay, dry-run, condition changes, source changes, source recovery, live paths, AI API calls, Discord notifications, MT5 orders, live hooks, or final signals.

NO_SIGNAL Discord notification remains disabled.

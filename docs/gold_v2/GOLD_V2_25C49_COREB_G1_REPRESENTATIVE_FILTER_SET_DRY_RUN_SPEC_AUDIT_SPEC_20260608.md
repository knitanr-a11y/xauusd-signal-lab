# GOLD V2 25C49 CoreB G1 representative filter set dry-run spec audit spec

Date: 2026-06-08

Step: `25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY`

Mode: audit-only dry-run specification package

## Purpose

25C49 reads the 25C48 representative filter set review spec artifacts and writes the dry-run specification package for the A002 representative filter set.

25C49 is not a dry-run execution step. It must not run replay, must not run a dry-run, must not approve A002/A004 or any variant, must not change sources or conditions, and must not enable any live/external action.

## Required inputs

From:

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

## Source-of-truth facts

25C49 must preserve these facts from 25C48:

```text
step = 25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY
status = COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_READY_AUDIT_ONLY
audit_only = true
spec_only = true
representative_variant_code = A002
representative_retention_priority_cutoff = 1
representative_total_unique_damage_keys = 69
representative_covered_unique_keys = 69
representative_open_unique_keys = 0
representative_retained_filter_count = 2
representative_filters = same_count>=2&unique_origins>=2, unique_origins>=2
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
next_recommended_step = 25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY
total_stop_rows = 0
```

All execution and external flags in the 25C48 summary must remain false.

## Output directory

```text
FX_OUTPUTS/gold_v2_25c49_coreb_g1_representative_filter_set_dry_run_spec_audit_only/
```

Expected files:

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

## Dry-run specification contents

25C49 should define, but not execute, the future dry-run package.

Required dry-run input contract rows:

```text
source 25C48 summary
source 25C48 representative filter set
source 25C46 selected coverage plan
source 25C45 corrected attribution rows
source 25C10 baseline replay signal rows or the exact audited replay source identified by the prior chain
```

The final dry-run execution step must use audited source-of-truth artifacts only. It must not approximate or reimplement exploration logic from memory.

Required dry-run output contract rows:

```text
dry-run summary json
dry-run candidate signal rows csv
dry-run key coverage audit csv
dry-run filter application audit csv
dry-run comparison against 25C48 expected keys
dry-run boundary and gate matrices
```

Required acceptance checks for any future execution:

```text
A002 remains the requested candidate
filter set exactly equals the two retained filters
expected unique damage keys = 69
expected open keys before dry-run = 0
no source recovery is implied
no live/external/AI/notification/order/final signal is enabled
manual review is required before any execution step
```

## Next recommended step

25C49 may recommend only a readiness review step, not execution:

```text
25C50_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY
```

25C50 must still be audit-only unless a later explicit instruction changes the boundary.

## Success status

```text
COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_READY_AUDIT_ONLY
```

## Stop statuses

```text
25C49_STOP_MISSING_INPUT_AUDIT_ONLY
25C49_STOP_25C48_CONTRACT_UNSAFE_AUDIT_ONLY
25C49_STOP_DRY_RUN_SPEC_UNSAFE_AUDIT_ONLY
```

## Boundaries

25C49 must not approve variants, must not execute replay or dry-run, must not mutate sources or conditions, must not unblock live evaluator, must not send Discord notifications, must not place MT5 orders, must not call AI API, must not run live hooks, and must not create final signals.

NO_SIGNAL Discord notification remains disabled.

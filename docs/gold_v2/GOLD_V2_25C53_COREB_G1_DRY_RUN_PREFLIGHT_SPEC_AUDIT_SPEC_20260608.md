# GOLD V2 25C53 CoreB G1 dry-run preflight spec audit spec

Date: 2026-06-08

Step: `25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY`

Mode: audit-only dry-run preflight specification

## Purpose

25C53 reads the 25C52 source candidate review artifacts and writes a preflight specification package for a future dry-run. It is still not a dry-run execution step.

25C53 must not run replay, must not run dry-run, must not approve A002/A004 or any variant, must not change sources or conditions, and must not enable live/external behavior.

## Required inputs

From:

```text
FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/
```

Required files:

```text
02_25c52_dry_run_source_candidate_review_summary.json
04_25c52_contract_audit.csv
05_25c52_candidate_file_metadata.csv
06_25c52_candidate_header_review.csv
07_25c52_source_binding_matrix.csv
08_25c52_execution_boundary_matrix.csv
09_25c52_gates.csv
10_25c52_next_step_plan.csv
11_25c52_handoff_notes.csv
```

## Source-of-truth facts from 25C52

25C53 must preserve these facts:

```text
step = 25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY
status = COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_READY_AUDIT_ONLY_SOURCE_BOUND_FOR_PLANNING_EXECUTION_BLOCKED
audit_only = true
source_candidate_review_only = true
representative_variant_code = A002
representative_filters = same_count>=2&unique_origins>=2, unique_origins>=2
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
candidate_relative_path = gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
candidate_file_exists = true
candidate_header_readable = true
candidate_column_count = 10
source_binding_status = SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY
source_confirmed_for_execution = false
future_dry_run_execution_allowed = false
next_recommended_step = 25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY
total_stop_rows = 0
```

All execution and external flags in the 25C52 summary must remain false.

## Expected source columns

The bound source candidate header must include:

```text
dataset
entry_time
policy
filter
source_count_by_entry_time
unique_origin_count_by_entry_time
same_count_threshold
unique_origins_threshold
intersection_only
full_coreb_parity
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/
```

Expected files:

```text
00_不要_25c53_file_request_list.csv
01_25c53_GOLD_V2_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY_REPORT.md
02_25c53_dry_run_preflight_spec_summary.json
03_25c53_input_audit.csv
04_25c53_contract_audit.csv
05_25c53_preflight_input_matrix.csv
06_25c53_preflight_check_matrix.csv
07_25c53_preflight_output_spec_matrix.csv
08_25c53_execution_boundary_matrix.csv
09_25c53_gates.csv
10_25c53_next_step_plan.csv
11_25c53_handoff_notes.csv
```

## Preflight specification items

25C53 should define the future preflight checks but not execute a dry-run:

```text
source candidate is bound for future audit planning only
source candidate has expected header columns
A002 representative filter set remains exact
A002 remains not approved
future dry-run must use unique key: variant + dataset + entry_time + policy
expected representative unique damage keys = 69
expected representative open keys = 0
future dry-run output must include summary, candidate rows, key coverage audit, filter application audit, comparison matrix, gates, and handoff
future dry-run execution remains blocked until a later explicit acceptance
```

## Next recommended step

25C53 may recommend only an execution gate review step, not execution:

```text
25C54_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY
```

25C54 must remain audit-only unless a later explicit instruction changes the boundary.

## Success status

```text
COREB_G1_DRY_RUN_PREFLIGHT_SPEC_READY_AUDIT_ONLY_EXECUTION_GATE_REVIEW_REQUIRED
```

## Stop statuses

```text
25C53_STOP_MISSING_INPUT_AUDIT_ONLY
25C53_STOP_25C52_CONTRACT_UNSAFE_AUDIT_ONLY
25C53_STOP_PREFLIGHT_SPEC_UNSAFE_AUDIT_ONLY
```

## Boundaries

25C53 must not approve variants, must not execute replay or dry-run, must not mutate sources or conditions, must not confirm source for execution, must not unblock live evaluator, must not send Discord notifications, must not place MT5 orders, must not call AI API, must not run live hooks, and must not create final signals.

NO_SIGNAL Discord notification remains disabled.

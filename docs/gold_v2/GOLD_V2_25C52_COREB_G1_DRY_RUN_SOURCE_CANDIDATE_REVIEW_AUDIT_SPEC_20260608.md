# GOLD V2 25C52 CoreB G1 dry-run source candidate review audit spec

Date: 2026-06-08

Step: `25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY`

Mode: audit-only source candidate review / binding package

## Purpose

25C52 reads the 25C51 source candidate matrix and reviews the top candidate as the proposed audited baseline replay signal source for a future dry-run package.

25C52 may bind a candidate for future audit planning only. It must not run replay, must not run dry-run, must not approve A002/A004 or any variant, must not change sources or conditions, and must not enable live/external behavior.

## Required inputs

From:

```text
FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/
```

Required files:

```text
02_25c51_dry_run_source_concretion_review_summary.json
04_25c51_contract_audit.csv
06_25c51_source_candidate_matrix.csv
07_25c51_source_selection_matrix.csv
08_25c51_execution_boundary_matrix.csv
09_25c51_gates.csv
10_25c51_next_step_plan.csv
11_25c51_handoff_notes.csv
```

## Source-of-truth facts from 25C51

25C52 must preserve these facts:

```text
step = 25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY
status = COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_READY_AUDIT_ONLY_SOURCE_CANDIDATE_REVIEW_REQUIRED
audit_only = true
source_concretion_review_only = true
representative_variant_code = A002
representative_filters = same_count>=2&unique_origins>=2, unique_origins>=2
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
source_candidate_review_required = true
future_dry_run_execution_allowed = false
source_confirmed = false
next_recommended_step = 25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY
total_stop_rows = 0
```

25C52 must preserve all execution and external flags as false.

## Top candidate expected from 25C51

```text
gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
```

This file may be reviewed as a future dry-run baseline source candidate. Binding is audit-only and does not authorize dry-run execution.

## Output directory

```text
FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/
```

Expected files:

```text
00_不要_25c52_file_request_list.csv
01_25c52_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
02_25c52_dry_run_source_candidate_review_summary.json
03_25c52_input_audit.csv
04_25c52_contract_audit.csv
05_25c52_candidate_file_metadata.csv
06_25c52_candidate_header_review.csv
07_25c52_source_binding_matrix.csv
08_25c52_execution_boundary_matrix.csv
09_25c52_gates.csv
10_25c52_next_step_plan.csv
11_25c52_handoff_notes.csv
```

## Candidate review checks

Required candidate review checks:

```text
top candidate path matches 25C51 selection
candidate file exists locally
candidate extension is .csv
candidate is non-empty
candidate has a readable header
candidate appears to be under FX_OUTPUTS
candidate status remains audit-only binding candidate
future dry-run execution remains blocked
```

If the candidate file exists and the header is readable, 25C52 may set:

```text
source_binding_status = SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY
source_confirmed_for_execution = false
future_dry_run_execution_allowed = false
```

## Next recommended step

25C52 may recommend only a future dry-run preflight specification step, not execution:

```text
25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY
```

25C53 must still be audit-only and must not execute dry-run unless a later explicit instruction changes the boundary.

## Success status

```text
COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_READY_AUDIT_ONLY_SOURCE_BOUND_FOR_PLANNING_EXECUTION_BLOCKED
```

## Stop statuses

```text
25C52_STOP_MISSING_INPUT_AUDIT_ONLY
25C52_STOP_25C51_CONTRACT_UNSAFE_AUDIT_ONLY
25C52_STOP_SOURCE_CANDIDATE_UNSAFE_AUDIT_ONLY
```

## Boundaries

25C52 must not approve variants, must not execute replay or dry-run, must not mutate sources or conditions, must not unblock live evaluator, must not send Discord notifications, must not place MT5 orders, must not call AI API, must not run live hooks, and must not create final signals.

NO_SIGNAL Discord notification remains disabled.

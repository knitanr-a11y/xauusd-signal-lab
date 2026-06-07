# GOLD V2 25C47 CoreB G1 filter coverage next plan audit spec

Date: 2026-06-08

Step: `25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY`

Mode: audit-only next-plan review

## Purpose

25C47 reads the reviewed 25C46 filter coverage artifacts and creates the next planning package. It must not execute replay, dry-run, condition changes, source changes, source recovery, live paths, external actions, AI review, Discord notification, MT5 order placement, or final signal creation.

25C47 is not approval of A002, A004, or any other variant. A002 remains only the representative candidate selected by the 25C46 tie rule.

## Required inputs

From:

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/
```

Required files:

```text
02_25c46_filter_coverage_review_summary.json
04_25c46_coverage_matrix.csv
05_25c46_selected_coverage_plan.csv
07_25c46_limits.csv
08_25c46_gates.csv
09_25c46_next_step_plan.csv
```

## Source-of-truth contract from 25C46

25C47 must validate the following 25C46 facts before writing a ready status:

```text
step = 25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY
logical_step_alias = 25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY
status = COREB_G1_FILTER_COVERAGE_REVIEW_READY_AUDIT_ONLY
known_unique_damage_keys = 360
unique_incremental_damage_keys = 360
filter_attribution_rows = 1260
unique_cleanly_attributed_damage_keys = 360
unique_not_cleanly_attributed_damage_keys = 0
coverage_rows = 11
full_coverage_candidate_rows = 7
selected_variant_code = A002
selected_retention_priority_cutoff = 1
selected_total_unique_damage_keys = 69
selected_covered_unique_keys = 69
selected_open_unique_keys = 0
selected_retained_filter_count = 2
selected_approval_status = NOT_APPROVED_REVIEW_ONLY
a002_a004_approval_status = NOT_APPROVED_REVIEW_ONLY
```

All execution and external flags in the 25C46 summary must remain false.

## 25C47 output directory

```text
FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/
```

Expected files:

```text
00_不要_25c47_file_request_list.csv
01_25c47_GOLD_V2_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY_REPORT.md
02_25c47_filter_coverage_next_plan_summary.json
03_25c47_input_audit.csv
04_25c47_contract_audit.csv
05_25c47_representative_candidate_review.csv
06_25c47_next_option_matrix.csv
07_25c47_execution_boundary_matrix.csv
08_25c47_gates.csv
09_25c47_next_step_plan.csv
10_25c47_handoff_notes.csv
```

## Plan logic

25C47 should preserve the selected 25C46 representative as a review candidate only:

```text
variant = A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U
variant_code = A002
retention_priority_cutoff = 1
total_unique_damage_keys = 69
covered_unique_keys = 69
open_unique_keys = 0
retained_filter_count = 2
approval_status = NOT_APPROVED_REVIEW_ONLY
execution_allowed_now = false
```

The next option matrix should separate:

```text
1. allowed audit-only specification work
2. blocked replay/dry-run execution
3. blocked condition/source changes
4. blocked live/external/AI/notification/order/final-signal actions
```

## Next recommended step

25C47 may recommend only a specification/review step, not execution:

```text
25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY
```

## Success status

```text
COREB_G1_FILTER_COVERAGE_NEXT_PLAN_READY_AUDIT_ONLY
```

## Stop statuses

```text
25C47_STOP_MISSING_INPUT_AUDIT_ONLY
25C47_STOP_25C46_CONTRACT_UNSAFE_AUDIT_ONLY
25C47_STOP_REPRESENTATIVE_CANDIDATE_UNSAFE_AUDIT_ONLY
```

## Boundaries

25C47 must not approve A002/A004, must not run any replay or dry-run, must not mutate sources or conditions, must not use AI API, must not send Discord notifications, must not place MT5 orders, must not run live hooks, and must not create final signals.

NO_SIGNAL Discord notification remains disabled.

# GOLD V2 25C48 CoreB G1 representative filter set review spec audit spec

Date: 2026-06-08

Step: `25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY`

Mode: audit-only specification/review

## Purpose

25C48 reads the 25C47 next-plan artifacts and the 25C46 selected coverage plan, then writes a representative filter set review specification for the A002 candidate. It is a specification step only.

25C48 must not approve A002/A004 or any other variant. It must not run replay, dry-run, source recovery, source mutation, condition changes, live hooks, AI API calls, Discord notifications, MT5 orders, or final signal creation.

## Required inputs

From:

```text
FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/
```

Required 25C47 files:

```text
02_25c47_filter_coverage_next_plan_summary.json
04_25c47_contract_audit.csv
05_25c47_representative_candidate_review.csv
06_25c47_next_option_matrix.csv
07_25c47_execution_boundary_matrix.csv
08_25c47_gates.csv
09_25c47_next_step_plan.csv
```

From:

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/
```

Required 25C46 file:

```text
05_25c46_selected_coverage_plan.csv
```

The 25C46 selected coverage plan is required because it contains the retained filter string for the representative candidate.

## Source-of-truth facts

25C48 must preserve these 25C47 facts:

```text
25C47 status = COREB_G1_FILTER_COVERAGE_NEXT_PLAN_READY_AUDIT_ONLY
representative_variant_code = A002
representative_retention_priority_cutoff = 1
representative_total_unique_damage_keys = 69
representative_covered_unique_keys = 69
representative_open_unique_keys = 0
representative_retained_filter_count = 2
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
next_recommended_step = 25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY
```

25C48 must preserve these 25C46 selected-plan facts:

```text
selected_representative = true
variant_code = A002
retention_priority_cutoff = 1
total_unique_damage_keys = 69
covered_unique_keys = 69
open_unique_keys = 0
retained_filter_count = 2
approval_status = NOT_APPROVED_REVIEW_ONLY
execution_allowed_now = false
requires_artifact_review_before_25c47 = true
retained_filters = same_count>=2&unique_origins>=2;unique_origins>=2
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c48_coreb_g1_representative_filter_set_review_spec_audit_only/
```

Expected files:

```text
00_不要_25c48_file_request_list.csv
01_25c48_GOLD_V2_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY_REPORT.md
02_25c48_representative_filter_set_review_spec_summary.json
03_25c48_input_audit.csv
04_25c48_contract_audit.csv
05_25c48_representative_filter_set.csv
06_25c48_review_spec_matrix.csv
07_25c48_blocked_execution_matrix.csv
08_25c48_gates.csv
09_25c48_next_step_plan.csv
10_25c48_handoff_notes.csv
```

## Review/spec logic

25C48 should split the retained filter string into one row per filter:

```text
1. same_count>=2&unique_origins>=2
2. unique_origins>=2
```

It should write a review specification that describes what a later dry-run specification would need to check, without running that dry-run.

Required review-spec items:

```text
filter set identity
coverage basis: unique key only
expected unique damage keys = 69
expected open keys = 0
representative candidate approval status remains NOT_APPROVED_REVIEW_ONLY
future dry-run remains blocked
source recovery remains blocked
live/external/AI actions remain blocked
```

## Next recommended step

25C48 may recommend only the next audit-only specification step:

```text
25C49_COREB_G1_REPRESENTATIVE_FILTER_SET_DRY_RUN_SPEC_AUDIT_ONLY
```

25C49 must still be a specification step. It must not run replay or dry-run unless a later explicit approval changes the boundary.

## Success status

```text
COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_READY_AUDIT_ONLY
```

## Stop statuses

```text
25C48_STOP_MISSING_INPUT_AUDIT_ONLY
25C48_STOP_25C47_CONTRACT_UNSAFE_AUDIT_ONLY
25C48_STOP_REPRESENTATIVE_FILTER_SET_UNSAFE_AUDIT_ONLY
```

## Boundaries

25C48 must not approve variants, must not execute replay/dry-run, must not mutate sources or conditions, must not unblock live evaluator, must not send Discord notifications, must not place MT5 orders, must not call AI API, must not run live hooks, and must not create final signals.

NO_SIGNAL Discord notification remains disabled.

# GOLD V2 25C2 CoreB intersection-only dry-run plan audit spec

Date: 2026-06-07
Step: `25C2_COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_AUDIT_ONLY`
Mode: audit-only implementation plan, no replay execution

## Purpose

25C1B showed all feature-source alignment gaps are before feature source start:

```text
raw_rows = 16875
covered_rows = 14748
gap_rows = 2127
BEFORE_FEATURE_START = 2127
WITHIN_FEATURE_RANGE_HOLE = 0
AFTER_FEATURE_END = 0
feature_min_time = 2025-02-20 12:15:00
feature_max_time = 2026-06-04 13:00:00
```

25C2 defines a strict intersection-only dry-run plan for the covered subset. This must not be promoted as full CoreB parity because 2,127 raw rows are outside the feature source range.

25C2 does not execute the dry-run. It only defines the contract, exclusions, gates, and next execution blocker.

## Upload request naming convention

```text
00_不要_...
01_...
02_...
03_...
```

`00` is unnecessary files. Required files start at `01`.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c1b_coreb_alignment_gap_review_audit_only/02_25c1b_coreb_alignment_gap_review_summary.json
FX_OUTPUTS/gold_v2_25c1b_coreb_alignment_gap_review_audit_only/04_25c1b_gap_classification_counts.csv
FX_OUTPUTS/gold_v2_25c1b_coreb_alignment_gap_review_audit_only/08_25c1b_alignment_decision_matrix.csv
```

## Outputs

```text
00_不要_25c2_file_request_list.csv
01_25c2_GOLD_V2_COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md
02_25c2_coreb_intersection_only_dry_run_plan_summary.json
03_25c2_input_audit.csv
04_25c2_intersection_scope_contract.csv
05_25c2_exclusion_impact_matrix.csv
06_25c2_dry_run_algorithm_contract.csv
07_25c2_acceptance_gate_matrix.csv
08_25c2_forbidden_methods.csv
09_25c2_next_step_plan.csv
```

## Contract

The next implementation may only evaluate CoreB frozen condition objects for raw rows whose `entry_time` exists in the feature source `time` column.

The next implementation must keep these facts explicit:

```text
intersection-only = true
full_coreb_parity = false
excluded_raw_rows = 2127
excluded_reason = BEFORE_FEATURE_START
```

## Safety

CoreB remains blocked. Source recovery execution, source mutation, final signal, live hook, Discord, MT5, and AI remain off.

Expected status:

```text
COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED
```

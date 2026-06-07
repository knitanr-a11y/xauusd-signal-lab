# GOLD V2 25C1B CoreB alignment gap review audit spec

Date: 2026-06-07
Step: `25C1B_COREB_ALIGNMENT_GAP_REVIEW_AUDIT_ONLY`
Mode: audit-only gap classification

## Purpose

25C1 showed raw ledger to feature-source time coverage is incomplete:

```text
raw_rows = 16875
raw_rows_found_in_feature = 14748
raw_rows_missing_feature_time = 2127
raw_time_coverage_ratio = 0.8739555555555556
```

25C1B classifies missing raw entry times into:

```text
BEFORE_FEATURE_START
AFTER_FEATURE_END
WITHIN_FEATURE_RANGE_HOLE
UNPARSED_RAW_TIME
```

25C1B does not execute CoreB replay, does not mutate source artifacts, does not compute same_count parity, and does not unblock CoreB.

## Upload request naming convention

Output request files use:

```text
00_不要_...
01_...
02_...
03_...
```

`00` is always the unnecessary-file list. Required files start at `01`.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_audit_only/02_25c1_coreb_feature_source_to_raw_ledger_alignment_plan_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

From those it resolves:

```text
feature source candidate CSV
rr125_raw_signal_ledger.csv
```

## Outputs

```text
00_不要_25c1b_file_request_list.csv
01_25c1b_GOLD_V2_COREB_ALIGNMENT_GAP_REVIEW_AUDIT_ONLY_REPORT.md
02_25c1b_coreb_alignment_gap_review_summary.json
03_25c1b_input_audit.csv
04_25c1b_gap_classification_counts.csv
05_25c1b_gap_by_dataset_policy.csv
06_25c1b_gap_time_bounds.csv
07_25c1b_gap_samples.csv
08_25c1b_alignment_decision_matrix.csv
09_25c1b_next_step_plan.csv
```

## Safety

CoreB remains blocked. Source recovery execution, source mutation, final signal, live hook, Discord, MT5, and AI remain off.

Expected status:

```text
COREB_ALIGNMENT_GAP_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED
```

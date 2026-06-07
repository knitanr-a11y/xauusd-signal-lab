# GOLD V2 25B6 CoreB dry-run parity review audit spec

Date: 2026-06-07
Step: `25B6_COREB_DRY_RUN_PARITY_REVIEW_AUDIT_ONLY`
Mode: audit-only review, no replay implementation changes

## Purpose

25B5 completed a dry-run key probe, but parity was not proven.

25B6 classifies why the 25B5 dry-run did not reproduce target parity. It reads only 25B5 outputs and produces a review matrix.

25B6 does not change source files, does not rerun CoreB logic, does not approve source recovery, and does not unblock CoreB.

## Inputs

```text
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/GOLD_V2_25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_AUDIT_ONLY_REPORT.md
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_coreb_same_count_replay_dry_run_summary.json
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_rule_key_audit.csv
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_raw_match_summary.csv
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_parity_summary.csv
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_target_compare_same_count_ge15.csv
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_dry_run_candidate_rows.csv
Files/FX_OUTPUTS/gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only/gold_v2_25b5_execution_blockers.csv
```

## Expected 25B5 facts

```text
target_ge15_unique_keys = 2012
dry_run_unique_keys = 17
matched_keys = 1
missing_dry_run_keys = 2011
extra_dry_run_keys = 16
selected rules 12 collapsed to 4 unique key rows
same_count source rules 33 collapsed to 14 unique key rows
source_rule_hit_rows = 16875
raw_rows = 16875
```

## Review conclusions to classify

25B6 must classify at least:

```text
KEY_ONLY_RULE_COLLAPSE
TARGET_FILTER_CONTRACT_MISMATCH
SOURCE_RULE_UNIVERSE_OVERBROAD_KEY_MATCH
DRY_RUN_UNDER_GENERATION
EXTRA_DRY_RUN_ROWS
SAME_COUNT_VALUE_PARITY_NOT_CHECKED
CLUSTER_MEMBERSHIP_NOT_CHECKED
COREB_UNBLOCK_FORBIDDEN
```

## Outputs

```text
GOLD_V2_25B6_COREB_DRY_RUN_PARITY_REVIEW_AUDIT_ONLY_REPORT.md
gold_v2_25b6_input_audit.csv
gold_v2_25b6_parity_review_matrix.csv
gold_v2_25b6_filter_gap_counts.csv
gold_v2_25b6_dry_run_entry_distribution.csv
gold_v2_25b6_review_decision_matrix.csv
gold_v2_25b6_next_step_plan.csv
gold_v2_25b6_coreb_dry_run_parity_review_summary.json
```

## Safety

All live/final/external flags remain false. CoreB remains blocked. 24AF pause is retained.

## Expected status

```text
COREB_DRY_RUN_PARITY_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED
```

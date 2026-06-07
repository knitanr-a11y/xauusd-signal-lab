# GOLD V2 25C25 CoreB G1 mismatch review audit spec

Date: 2026-06-07
Step: `25C25_COREB_G1_MISMATCH_REVIEW_AUDIT_ONLY`
Mode: audit-only result review

## Purpose

25C24 completed the approved G1 entry-level dry-run and showed mismatch remains:

```text
both = 168
left_only = 813
right_only = 78
```

25C25 reviews the G1 mismatch balance and determines the next audit-only review target.

## Outputs

```text
00_不要_25c25_file_request_list.csv
01_25c25_GOLD_V2_COREB_G1_MISMATCH_REVIEW_AUDIT_ONLY_REPORT.md
02_25c25_coreb_g1_mismatch_review_summary.json
03_25c25_input_audit.csv
04_25c25_g1_mismatch_balance_matrix.csv
05_25c25_g1_dataset_skew_matrix.csv
06_25c25_g1_sample_time_bounds.csv
07_25c25_g1_mismatch_review_decision_matrix.csv
08_25c25_next_step_plan.csv
```

Expected status:

```text
COREB_G1_MISMATCH_REVIEW_COMPLETED_AUDIT_ONLY_LEFT_ONLY_DOMINANT_REVIEW_REQUIRED
```

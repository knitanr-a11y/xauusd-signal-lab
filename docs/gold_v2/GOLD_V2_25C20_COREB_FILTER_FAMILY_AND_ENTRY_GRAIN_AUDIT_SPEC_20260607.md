# GOLD V2 25C20 CoreB filter family and entry grain audit spec

Date: 2026-06-07
Step: `25C20_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY`
Mode: audit-only review, no dry-run execution

## Purpose

25C19 selected the next safe review target before another dry-run. 25C20 reviews two dimensions only:

```text
1. filter family mismatch
2. entry_time grain / multiplicity
```

No CoreB condition is changed. No replay execution is performed.

## Outputs

```text
00_不要_25c20_file_request_list.csv
01_25c20_GOLD_V2_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY_REPORT.md
02_25c20_coreb_filter_family_and_entry_grain_summary.json
03_25c20_input_audit.csv
04_25c20_filter_family_mismatch_matrix.csv
05_25c20_replay_entry_grain_distribution.csv
06_25c20_target_entry_grain_distribution.csv
07_25c20_entry_grain_compare_matrix.csv
08_25c20_grain_review_decision_matrix.csv
09_25c20_next_step_plan.csv
```

Expected status:

```text
COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_COMPLETED_AUDIT_ONLY_GRAIN_CONTRACT_REVIEW_REQUIRED
```

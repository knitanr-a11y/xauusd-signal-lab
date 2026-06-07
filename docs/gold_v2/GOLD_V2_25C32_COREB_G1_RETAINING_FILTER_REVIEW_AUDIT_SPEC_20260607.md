# GOLD V2 25C32 CoreB G1 retaining filter review audit spec

Date: 2026-06-07
Step: `25C32_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY`
Mode: audit-only retaining-filter review

## Purpose

25C31 confirmed that 25C30 had zero G1-count effect because all primary-filter G1 keys were retained by other filters.

25C32 identifies the non-primary filters retaining those G1 keys. Because 25C31 had no reliable retaining filter family label, this step derives filter family from the filter expression text.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c31_coreb_g1_narrowed_dry_run_result_review_audit_only/02_25c31_coreb_g1_narrowed_dry_run_result_review_summary.json
FX_OUTPUTS/gold_v2_25c31_coreb_g1_narrowed_dry_run_result_review_audit_only/05_25c31_primary_filter_key_retention_matrix.csv
FX_OUTPUTS/gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only/04_25c30_candidate_execution_contract.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
```

## Outputs

```text
00_不要_25c32_file_request_list.csv
01_25c32_GOLD_V2_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY_REPORT.md
02_25c32_coreb_g1_retaining_filter_review_summary.json
03_25c32_input_audit.csv
04_25c32_retaining_filter_driver_matrix.csv
05_25c32_retaining_filter_family_matrix.csv
06_25c32_retention_count_distribution.csv
07_25c32_retaining_filter_review_decision_matrix.csv
08_25c32_next_step_plan.csv
```

Expected status:

```text
COREB_G1_RETAINING_FILTER_REVIEW_COMPLETED_AUDIT_ONLY_RETENTION_AWARE_NARROWING_PLAN_REQUIRED
```

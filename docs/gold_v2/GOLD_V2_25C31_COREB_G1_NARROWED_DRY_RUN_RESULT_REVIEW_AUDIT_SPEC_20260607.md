# GOLD V2 25C31 CoreB G1 narrowed dry-run result review audit spec

Date: 2026-06-07
Step: `25C31_COREB_G1_NARROWED_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY`
Mode: audit-only result review

## Purpose

25C30 simulated removal of the 25C29 PRIMARY_REVIEW filters, but G1 counts did not change.

25C31 reviews the no-effect result and checks whether the same G1 keys remain covered by other replay filters.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only/02_25c30_coreb_g1_narrowed_dry_run_summary.json
FX_OUTPUTS/gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only/04_25c30_candidate_execution_contract.csv
FX_OUTPUTS/gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only/05_25c30_variant_compare_matrix.csv
FX_OUTPUTS/gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only/06_25c30_variant_delta_matrix.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
```

## Outputs

```text
00_不要_25c31_file_request_list.csv
01_25c31_GOLD_V2_COREB_G1_NARROWED_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c31_coreb_g1_narrowed_dry_run_result_review_summary.json
03_25c31_input_audit.csv
04_25c31_no_effect_delta_review.csv
05_25c31_primary_filter_key_retention_matrix.csv
06_25c31_retaining_filter_family_matrix.csv
07_25c31_result_review_decision_matrix.csv
08_25c31_next_step_plan.csv
```

Expected status:

```text
COREB_G1_NARROWED_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_G1_KEY_RETENTION_REVIEW_REQUIRED
```

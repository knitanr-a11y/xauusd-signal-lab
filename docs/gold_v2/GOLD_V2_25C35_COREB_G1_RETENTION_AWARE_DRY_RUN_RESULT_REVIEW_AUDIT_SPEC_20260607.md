# GOLD V2 25C35 CoreB G1 retention-aware dry-run result review audit spec

Date: 2026-06-07
Step: `25C35_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY`
Mode: audit-only result review

## Purpose

25C34 ran retention-aware dry-run variants. B002 reduced left_only strongly but increased right_only and reduced both.

25C35 reviews the trade-off and identifies whether the best variant is usable as-is or requires a less destructive narrowing plan.

## Non-goals

```text
No source recovery.
No source mutation.
No live evaluator unblock.
No final signal.
No condition mutation.
```

## Inputs

```text
FX_OUTPUTS/gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only/02_25c34_coreb_g1_retention_aware_dry_run_summary.json
FX_OUTPUTS/gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only/04_25c34_variant_filter_contract.csv
FX_OUTPUTS/gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only/05_25c34_variant_compare_matrix.csv
FX_OUTPUTS/gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only/06_25c34_variant_delta_matrix.csv
FX_OUTPUTS/gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only/07_25c34_variant_by_dataset_policy.csv
FX_OUTPUTS/gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only/09_25c34_acceptance_gate_matrix.csv
```

## Outputs

```text
00_不要_25c35_file_request_list.csv
01_25c35_GOLD_V2_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c35_coreb_g1_retention_aware_dry_run_result_review_summary.json
03_25c35_input_audit.csv
04_25c35_variant_tradeoff_matrix.csv
05_25c35_best_variant_review_matrix.csv
06_25c35_over_narrowing_decision_matrix.csv
07_25c35_next_step_plan.csv
```

Expected status:

```text
COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_OVER_NARROWING_ADJUSTMENT_REQUIRED
```

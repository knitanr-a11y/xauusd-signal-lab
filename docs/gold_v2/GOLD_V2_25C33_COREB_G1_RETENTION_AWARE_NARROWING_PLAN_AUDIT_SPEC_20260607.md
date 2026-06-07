# GOLD V2 25C33 CoreB G1 retention-aware narrowing plan audit spec

Date: 2026-06-07
Step: `25C33_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY`
Mode: audit-only plan

## Purpose

25C32 showed that the 25C30 PRIMARY filters had no G1 effect because the same keys were retained by non-primary filters. The top retaining filter was `unique_origins>=2`.

25C33 creates a retention-aware narrowing plan. It does not run a narrowed replay and does not change rule conditions.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c32_coreb_g1_retaining_filter_review_audit_only/02_25c32_coreb_g1_retaining_filter_review_summary.json
FX_OUTPUTS/gold_v2_25c32_coreb_g1_retaining_filter_review_audit_only/04_25c32_retaining_filter_driver_matrix.csv
FX_OUTPUTS/gold_v2_25c32_coreb_g1_retaining_filter_review_audit_only/05_25c32_retaining_filter_family_matrix.csv
FX_OUTPUTS/gold_v2_25c32_coreb_g1_retaining_filter_review_audit_only/06_25c32_retention_count_distribution.csv
FX_OUTPUTS/gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only/04_25c30_candidate_execution_contract.csv
```

## Outputs

```text
00_不要_25c33_file_request_list.csv
01_25c33_GOLD_V2_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY_REPORT.md
02_25c33_coreb_g1_retention_aware_narrowing_plan_summary.json
03_25c33_input_audit.csv
04_25c33_retention_aware_bundle_matrix.csv
05_25c33_bundle_filter_membership.csv
06_25c33_execution_boundary_matrix.csv
07_25c33_acceptance_gate_matrix.csv
08_25c33_next_step_plan.csv
```

Expected status:

```text
COREB_G1_RETENTION_AWARE_NARROWING_PLAN_READY_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_DRY_RUN
```

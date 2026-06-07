# GOLD V2 25C34 CoreB G1 retention-aware dry-run audit spec

Date: 2026-06-07
Step: `25C34_COREB_G1_RETENTION_AWARE_DRY_RUN_AUDIT_ONLY`
Mode: audit-only dry-run

## Human acceptance

25C33 retention-aware narrowing plan was explicitly accepted before this step.

## Purpose

Run audit-only G1 dry-run comparisons for the 25C33 retention-aware bundles.

Variants:

```text
BASELINE_CURRENT
B001_PRIMARY_PLUS_TOP_RETAINER
B002_PRIMARY_PLUS_TOP5_RETAINERS
B003_UNIQUE_ORIGINS_RETAINERS_ONLY
```

## Non-goals

```text
No source recovery.
No source mutation.
No live evaluator unblock.
No final signal.
```

## Inputs

```text
FX_OUTPUTS/gold_v2_25c33_coreb_g1_retention_aware_narrowing_plan_audit_only/02_25c33_coreb_g1_retention_aware_narrowing_plan_summary.json
FX_OUTPUTS/gold_v2_25c33_coreb_g1_retention_aware_narrowing_plan_audit_only/04_25c33_retention_aware_bundle_matrix.csv
FX_OUTPUTS/gold_v2_25c33_coreb_g1_retention_aware_narrowing_plan_audit_only/05_25c33_bundle_filter_membership.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
FX_OUTPUTS/gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only/02_25c15_coreb_selected_policy_replay_contract_summary.json
FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

## Outputs

```text
00_不要_25c34_file_request_list.csv
01_25c34_GOLD_V2_COREB_G1_RETENTION_AWARE_DRY_RUN_AUDIT_ONLY_REPORT.md
02_25c34_coreb_g1_retention_aware_dry_run_summary.json
03_25c34_input_audit.csv
04_25c34_variant_filter_contract.csv
05_25c34_variant_compare_matrix.csv
06_25c34_variant_delta_matrix.csv
07_25c34_variant_by_dataset_policy.csv
08_25c34_best_variant_left_only_samples.csv
09_25c34_acceptance_gate_matrix.csv
10_25c34_next_step_plan.csv
```

Expected status when mismatch remains:

```text
COREB_G1_RETENTION_AWARE_DRY_RUN_COMPLETED_AUDIT_ONLY_RESULT_REVIEW_REQUIRED
```

# GOLD V2 25C24 CoreB G1 entry-level review dry-run audit spec

Date: 2026-06-07
Step: `25C24_COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_AUDIT_ONLY`
Mode: audit-only dry-run

## Purpose

Run the approved G1 entry-level audit-only comparison.

G1 key:

```text
dataset
entry_time
policy
```

The comparison is read-only and writes audit artifacts only.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c23_coreb_g1_entry_level_review_plan_audit_only/02_25c23_coreb_g1_entry_level_review_plan_summary.json
FX_OUTPUTS/gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only/02_25c15_coreb_selected_policy_replay_contract_summary.json
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

## Outputs

```text
00_不要_25c24_file_request_list.csv
01_25c24_GOLD_V2_COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_AUDIT_ONLY_REPORT.md
02_25c24_coreb_g1_entry_level_review_dry_run_summary.json
03_25c24_input_audit.csv
04_25c24_g1_entry_compare_matrix.csv
05_25c24_g1_compare_by_dataset_policy.csv
06_25c24_g1_left_only_samples.csv
07_25c24_g1_right_only_samples.csv
08_25c24_g1_acceptance_gate_matrix.csv
09_25c24_next_step_plan.csv
```

Expected status when mismatch remains:

```text
COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_COMPLETED_AUDIT_ONLY_G1_MISMATCH_REVIEW_REQUIRED
```

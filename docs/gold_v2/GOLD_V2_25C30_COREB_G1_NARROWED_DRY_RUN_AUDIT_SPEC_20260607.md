# GOLD V2 25C30 CoreB G1 narrowed dry-run audit spec

Date: 2026-06-07
Step: `25C30_COREB_G1_NARROWED_DRY_RUN_AUDIT_ONLY`
Mode: audit-only dry-run

## Human acceptance

25C29 candidate review was explicitly accepted before this step.

## Purpose

Run an audit-only G1 comparison using the 25C29 PRIMARY_REVIEW candidate set as a simulated narrowing mask.

The dry-run compares:

```text
BASELINE_CURRENT
NARROW_PRIMARY_ONLY
```

The G1 comparison key remains:

```text
dataset
entry_time
policy
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
FX_OUTPUTS/gold_v2_25c29_coreb_g1_narrowing_candidate_review_audit_only/02_25c29_coreb_g1_narrowing_candidate_review_summary.json
FX_OUTPUTS/gold_v2_25c29_coreb_g1_narrowing_candidate_review_audit_only/04_25c29_candidate_review_matrix.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
FX_OUTPUTS/gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only/02_25c15_coreb_selected_policy_replay_contract_summary.json
FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

## Outputs

```text
00_不要_25c30_file_request_list.csv
01_25c30_GOLD_V2_COREB_G1_NARROWED_DRY_RUN_AUDIT_ONLY_REPORT.md
02_25c30_coreb_g1_narrowed_dry_run_summary.json
03_25c30_input_audit.csv
04_25c30_candidate_execution_contract.csv
05_25c30_variant_compare_matrix.csv
06_25c30_variant_delta_matrix.csv
07_25c30_variant_by_dataset_policy.csv
08_25c30_best_variant_left_only_samples.csv
09_25c30_acceptance_gate_matrix.csv
10_25c30_next_step_plan.csv
```

Expected status when mismatch remains:

```text
COREB_G1_NARROWED_DRY_RUN_COMPLETED_AUDIT_ONLY_MISMATCH_REVIEW_REQUIRED
```

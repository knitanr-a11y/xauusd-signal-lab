# GOLD V2 25C10 CoreB target filter contract replay dry-run audit spec

Date: 2026-06-07
Step: `25C10_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY`
Mode: audit-only filter-specific diagnostic replay

## Purpose

25C10B approved the next audit-only filter replay step. 25C10 executes filter-specific diagnostic replay using the filter contract plan from 25C9 and the unique-origin metric from 25C10A.

## Replay contract

For each target filter contract row:

```text
selected_hit_by_entry_time = True
AND if same_count_threshold exists: source_count_by_entry_time >= same_count_threshold
AND if unique_origins_threshold exists: unique_origin_count_by_entry_time >= unique_origins_threshold
```

The output key is filter-level:

```text
dataset + entry_time + policy + filter
```

Target comparison is performed at the same filter-level key.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c10b_coreb_filter_replay_execution_decision_audit_only/02_25c10b_coreb_filter_replay_execution_decision_summary.json
FX_OUTPUTS/gold_v2_25c9_coreb_target_filter_contract_replay_plan_audit_only/04_25c9_filter_contract_plan.csv
FX_OUTPUTS/gold_v2_25c10a_coreb_unique_origin_metric_derivation_audit_only/04_25c10a_unique_origin_counts_by_entry_time.csv
FX_OUTPUTS/gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only/08_25c3_selected_rule_hit_rows.csv
FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

## Outputs

```text
00_不要_25c10_file_request_list.csv
01_25c10_GOLD_V2_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY_REPORT.md
02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json
03_25c10_input_audit.csv
04_25c10_filter_replay_signal_rows.csv
05_25c10_filter_level_compare_matrix.csv
06_25c10_filter_compare_by_contract.csv
07_25c10_extra_signal_samples.csv
08_25c10_missing_target_samples.csv
09_25c10_replay_gate_matrix.csv
10_25c10_next_step_plan.csv
```

## Safety

CoreB remains blocked. This is not source recovery. No mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED
```

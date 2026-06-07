# GOLD V2 25C8 CoreB mismatch root cause audit spec

Date: 2026-06-07
Step: `25C8_COREB_MISMATCH_ROOT_CAUSE_AUDIT_ONLY`
Mode: audit-only root cause classification

## Purpose

25C7 still has in-scope mismatches after feature-scope filtering and policy expansion:

```text
in_scope_both = 103
in_scope_left_only = 587
in_scope_right_only = 298
```

25C8 classifies the remaining mismatch causes without changing CoreB conditions.

## Root-cause dimensions

25C8 must classify at least:

```text
1. target filter threshold mismatch: same_count>=8/10/15/20 etc.
2. unsupported target filter dimension: unique_origins>=2 etc.
3. signal entry not present in any target filter row
4. target entry present only under filter/policy not represented by current diagnostic signal contract
5. source_count threshold pass/fail by entry_time aggregate
```

## Inputs

```text
FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json
FX_OUTPUTS/gold_v2_25c5_coreb_intersection_dry_run_aggregated_revision_audit_only/04_25c5_aggregated_entry_signal_rows.csv
FX_OUTPUTS/gold_v2_25c4_coreb_intersection_dry_run_review_audit_only/05_25c4_entry_time_aggregate_distribution.csv
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

## Outputs

```text
00_不要_25c8_file_request_list.csv
01_25c8_GOLD_V2_COREB_MISMATCH_ROOT_CAUSE_AUDIT_ONLY_REPORT.md
02_25c8_coreb_mismatch_root_cause_summary.json
03_25c8_input_audit.csv
04_25c8_target_filter_inventory.csv
05_25c8_missing_root_cause_matrix.csv
06_25c8_extra_root_cause_matrix.csv
07_25c8_threshold_filter_alignment_matrix.csv
08_25c8_policy_root_cause_matrix.csv
09_25c8_root_cause_decision_matrix.csv
10_25c8_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_MISMATCH_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_FILTER_CONTRACT_REVIEW_REQUIRED
```

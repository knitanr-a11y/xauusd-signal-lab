# GOLD V2 25C7 CoreB target compare mismatch triage audit spec

Date: 2026-06-07
Step: `25C7_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY`
Mode: audit-only mismatch triage

## Purpose

25C6 compared aggregated diagnostic entries against target and found mismatches:

```text
entry_level_both = 103
entry_level_left_only = 587
entry_level_right_only = 368
```

25C7 triages why those mismatches exist. It does not change CoreB conditions and does not unblock CoreB.

## Required triage dimensions

25C7 must separate at least:

```text
1. target entries before feature source start / outside intersection scope
2. policy expansion issues from selected_policies
3. filter-level target multiplicity
4. true in-scope extra diagnostic entries
5. true in-scope missing target entries
```

## Inputs

```text
FX_OUTPUTS/gold_v2_25c6_coreb_intersection_aggregated_result_review_audit_only/02_25c6_coreb_intersection_aggregated_result_review_summary.json
FX_OUTPUTS/gold_v2_25c5_coreb_intersection_dry_run_aggregated_revision_audit_only/04_25c5_aggregated_entry_signal_rows.csv
FX_OUTPUTS/gold_v2_25c1b_coreb_alignment_gap_review_audit_only/02_25c1b_coreb_alignment_gap_review_summary.json
FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
```

## Outputs

```text
00_不要_25c7_file_request_list.csv
01_25c7_GOLD_V2_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY_REPORT.md
02_25c7_coreb_target_compare_mismatch_triage_summary.json
03_25c7_input_audit.csv
04_25c7_in_scope_entry_compare_matrix.csv
05_25c7_policy_expanded_compare_matrix.csv
06_25c7_target_scope_classification.csv
07_25c7_filter_multiplicity_matrix.csv
08_25c7_true_extra_samples.csv
09_25c7_true_missing_samples.csv
10_25c7_triage_decision_matrix.csv
11_25c7_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_TARGET_COMPARE_MISMATCH_TRIAGE_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED
```

# GOLD V2 25C17 CoreB selected-scope mismatch root cause audit spec

Date: 2026-06-07
Step: `25C17_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY`
Mode: audit-only residual mismatch review

## Purpose

25C16 separated source-only target policy rows and confirmed the remaining direct selected-output mismatch:

```text
selected_scope_both = 849
selected_scope_left_only = 4444
selected_scope_right_only = 1128
```

25C17 reviews the remaining RR1 selected-scope mismatch by filter and threshold. It does not change CoreB logic and does not enable CoreB.

## Outputs

```text
00_不要_25c17_file_request_list.csv
01_25c17_GOLD_V2_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY_REPORT.md
02_25c17_coreb_selected_scope_mismatch_root_cause_summary.json
03_25c17_input_audit.csv
04_25c17_selected_scope_filter_root_cause_matrix.csv
05_25c17_overgeneration_threshold_profile.csv
06_25c17_missing_threshold_profile.csv
07_25c17_root_cause_decision_matrix.csv
08_25c17_next_step_plan.csv
```

Expected status:

```text
COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_REPLAY_CONTRACT_REVIEW_REQUIRED
```

# GOLD V2 25C18 CoreB replay contract review audit spec

Date: 2026-06-07
Step: `25C18_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY`
Mode: audit-only contract review

## Purpose

25C17 showed the selected-scope residual mismatch:

```text
both = 849
left_only = 4444
right_only = 1128
low_threshold_overgeneration_rows = 4078
high_threshold_missing_rows = 310
```

25C18 reviews whether the current replay contract is acceptable as-is. It does not change CoreB logic and does not run replay.

## Review dimensions

```text
1. low threshold filter over-generation
2. high threshold filter missing rows
3. repeated filter families creating multiplicity
4. entry_time aggregation assumptions
5. whether another dry-run is justified
```

## Outputs

```text
00_不要_25c18_file_request_list.csv
01_25c18_GOLD_V2_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c18_coreb_replay_contract_review_summary.json
03_25c18_input_audit.csv
04_25c18_contract_issue_matrix.csv
05_25c18_replay_contract_review_decision_matrix.csv
06_25c18_forbidden_actions.csv
07_25c18_next_step_plan.csv
```

Expected status:

```text
COREB_REPLAY_CONTRACT_REVIEW_COMPLETED_AUDIT_ONLY_CONTRACT_REVISION_PLAN_REQUIRED
```

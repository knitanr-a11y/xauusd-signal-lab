# GOLD V2 25C10B CoreB filter replay execution decision audit spec

Date: 2026-06-07
Step: `25C10B_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY`
Mode: audit-only decision review, no filter replay execution

## Purpose

25C10A derived `unique_origin_count_by_entry_time`, but 25C10 target filter replay was still blocked pending review. 25C10B reviews whether the metric derivation is sufficient to allow the next audit-only replay step.

## Decision boundary

25C10B does not execute target filter replay.

It may only set the next step to ready if all are true:

```text
25C10A status clean
unique origin metric derived
source_count metric already available
filter readiness after derivation is true
CoreB condition_changed = false
full_coreb_parity = false
all live/source/external actions remain blocked
```

## Outputs

```text
00_不要_25c10b_file_request_list.csv
01_25c10b_GOLD_V2_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY_REPORT.md
02_25c10b_coreb_filter_replay_execution_decision_summary.json
03_25c10b_input_audit.csv
04_25c10b_metric_review_matrix.csv
05_25c10b_filter_replay_readiness_matrix.csv
06_25c10b_execution_decision_matrix.csv
07_25c10b_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_FILTER_REPLAY_EXECUTION_DECISION_COMPLETED_AUDIT_ONLY_25C10_READY
```

# GOLD V2 25C4 CoreB intersection dry-run review audit spec

Date: 2026-06-07
Step: `25C4_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY`
Mode: audit-only review

## Purpose

25C3 produced zero diagnostic signal rows even though selected rule hits existed:

```text
selected_rule_hit_rows = 11918
diagnostic_signal_rows = 0
```

25C4 reviews whether the zero-row result is valid or caused by same_count/source_universe aggregation granularity.

## Specific review focus

The CoreB entry logic is supposed to use an entry-time-level source universe count:

```text
selected_rule_hit AND source_universe_hit_count_by_entry_time >= 15
```

25C4 must compare:

```text
row-level source_universe_hit_count
entry-time aggregated source_universe_hit_count sum
entry-time selected hit presence
```

If entry-time aggregation can reach >=15 while row-level count cannot, 25C3 must be treated as implementation-review-blocked, not accepted as final diagnostic.

## Outputs

```text
00_不要_25c4_file_request_list.csv
01_25c4_GOLD_V2_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY_REPORT.md
02_25c4_coreb_intersection_dry_run_review_summary.json
03_25c4_input_audit.csv
04_25c4_source_count_granularity_matrix.csv
05_25c4_entry_time_aggregate_distribution.csv
06_25c4_selected_and_source_entry_candidates.csv
07_25c4_review_decision_matrix.csv
08_25c4_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_INTERSECTION_DRY_RUN_REVIEW_COMPLETED_AUDIT_ONLY_AGGREGATION_REVISION_REQUIRED
```

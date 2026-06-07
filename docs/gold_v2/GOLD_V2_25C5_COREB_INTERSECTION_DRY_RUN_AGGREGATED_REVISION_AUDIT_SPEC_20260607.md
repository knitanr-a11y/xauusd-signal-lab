# GOLD V2 25C5 CoreB intersection dry-run aggregated revision audit spec

Date: 2026-06-07
Step: `25C5_COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_AUDIT_ONLY`
Mode: audit-only diagnostic revision

## Purpose

25C4 proved 25C3 zero-signal output was caused by row-level source count granularity. 25C5 revises the diagnostic dry-run to apply the planned entry-time aggregation without changing CoreB conditions.

25C5 uses existing 25C3 condition-object evaluation outputs and aggregates source universe counts by `dataset + entry_time`.

## Required logic

```text
source_count_by_entry_time = sum(source_universe_hit_count per dataset+entry_time)
selected_hit_by_entry_time = any selected rule hit per dataset+entry_time
signal_entry = selected_hit_by_entry_time AND source_count_by_entry_time >= 15
```

This is still intersection-only and not full CoreB parity.

## Outputs

```text
00_不要_25c5_file_request_list.csv
01_25c5_GOLD_V2_COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_AUDIT_ONLY_REPORT.md
02_25c5_coreb_intersection_dry_run_aggregated_revision_summary.json
03_25c5_input_audit.csv
04_25c5_aggregated_entry_signal_rows.csv
05_25c5_aggregated_entry_distribution.csv
06_25c5_target_compare_summary.csv
07_25c5_review_gate_matrix.csv
08_25c5_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED
```

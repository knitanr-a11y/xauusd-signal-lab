# GOLD V2 25C3 CoreB intersection-only dry-run implementation audit spec

Date: 2026-06-07
Step: `25C3_COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY`
Mode: audit-only diagnostic dry-run execution

## Human acceptance condition

25C3 may run only with explicit intersection-only acceptance.

User acceptance statement context:

```text
CoreBの条件が変わらなければ問題ないです
```

This is interpreted only as acceptance of an audit-only diagnostic dry-run under the following constraints:

```text
CoreB frozen conditions are not changed.
2,127 pre-feature-start raw rows remain excluded.
intersection_only = true
full_coreb_parity = false
source_recovery_execution = false
live/final/external action = false
```

## Purpose

25C3 evaluates frozen CoreB condition objects on the 14,748 raw rows whose `entry_time` exists in the accepted feature source `time` column.

It is diagnostic only. It cannot prove full CoreB parity because 2,127 raw rows are outside feature coverage.

## Required logic

Use frozen source-of-truth config objects only:

```text
selected rules: frozen CoreB combined evaluator selected_rules or frozen source_rule_conditions fallback
source universe rules: frozen_coreB_same_count_source_universe_20260604.json source_universe_rules
entry logic: selected_rule_hit AND source_universe_hit_count_by_entry_time >= 15
```

The implementation must evaluate full condition objects, not KEY_COLS-only replay.

## Forbidden

```text
No feature value backfill
No missing pre-feature row filling
No target fitting
No static KEY_COLS-only replay
No source mutation
No source recovery execution
No live evaluator unblock
No final signal
No Discord/MT5/AI/live hook
```

## Outputs

```text
00_不要_25c3_file_request_list.csv
01_25c3_GOLD_V2_COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md
02_25c3_coreb_intersection_only_dry_run_implementation_summary.json
03_25c3_input_audit.csv
04_25c3_resolved_source_paths.csv
05_25c3_rule_schema_audit.csv
06_25c3_intersection_join_summary.csv
07_25c3_source_universe_hit_counts_by_entry.csv
08_25c3_selected_rule_hit_rows.csv
09_25c3_diagnostic_signal_rows.csv
10_25c3_target_compare_summary.csv
11_25c3_acceptance_gate_matrix.csv
12_25c3_next_step_plan.csv
```

Expected status:

```text
COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_REVIEW_REQUIRED
```

CoreB remains blocked regardless of row counts until a later review explicitly accepts the diagnostic result.

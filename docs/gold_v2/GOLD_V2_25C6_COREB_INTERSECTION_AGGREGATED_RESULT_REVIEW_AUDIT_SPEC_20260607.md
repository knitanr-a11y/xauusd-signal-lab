# GOLD V2 25C6 CoreB intersection aggregated result review audit spec

Date: 2026-06-07
Step: `25C6_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY`
Mode: audit-only target comparison review

## Purpose

25C5 produced 690 aggregated entry-time diagnostic signals without changing CoreB conditions.

25C6 compares those diagnostic entries against the target top ledger, without claiming full CoreB parity.

## Key contract

Because 25C5 signals are entry-time aggregate rows, compare primarily on:

```text
dataset + entry_time + policy
```

Target top ledger contains multiple filter rows per entry time, so 25C6 must report both:

```text
entry-level comparison
filter-level target coverage
```

## Outputs

```text
00_不要_25c6_file_request_list.csv
01_25c6_GOLD_V2_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c6_coreb_intersection_aggregated_result_review_summary.json
03_25c6_input_audit.csv
04_25c6_target_key_contract.csv
05_25c6_entry_level_compare_matrix.csv
06_25c6_filter_level_compare_matrix.csv
07_25c6_signal_extra_samples.csv
08_25c6_target_missing_samples.csv
09_25c6_review_gate_matrix.csv
10_25c6_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_TARGET_MISMATCH_REVIEW_REQUIRED
```

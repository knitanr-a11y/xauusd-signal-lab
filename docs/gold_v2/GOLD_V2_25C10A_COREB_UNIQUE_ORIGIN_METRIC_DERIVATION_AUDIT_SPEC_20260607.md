# GOLD V2 25C10A CoreB unique origin metric derivation audit spec

Date: 2026-06-07
Step: `25C10A_COREB_UNIQUE_ORIGIN_METRIC_DERIVATION_AUDIT_ONLY`
Mode: audit-only metric derivation, no filter replay

## Purpose

25C9 showed that filter-specific replay cannot cover unique-origins target filters until a metric is derived:

```text
unique_origin_count_by_entry_time
```

25C10A derives this metric from existing source-universe condition evaluation output. It does not execute target filter replay and does not change CoreB conditions.

## Metric contract

For each `dataset + entry_time + policy`:

```text
source_universe_active_row = source_universe_hit_count > 0
unique_origin_count_by_entry_time = count distinct origin_id among active source-universe rows
source_count_by_entry_time = sum source_universe_hit_count across rows
```

The metric is diagnostic and intersection-only.

## Inputs

```text
FX_OUTPUTS/gold_v2_25c9_coreb_target_filter_contract_replay_plan_audit_only/02_25c9_coreb_target_filter_contract_replay_plan_summary.json
FX_OUTPUTS/gold_v2_25c9_coreb_target_filter_contract_replay_plan_audit_only/04_25c9_filter_contract_plan.csv
FX_OUTPUTS/gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only/07_25c3_source_universe_hit_counts_by_entry.csv
```

## Outputs

```text
00_不要_25c10a_file_request_list.csv
01_25c10a_GOLD_V2_COREB_UNIQUE_ORIGIN_METRIC_DERIVATION_AUDIT_ONLY_REPORT.md
02_25c10a_coreb_unique_origin_metric_derivation_summary.json
03_25c10a_input_audit.csv
04_25c10a_unique_origin_counts_by_entry_time.csv
05_25c10a_unique_origin_distribution.csv
06_25c10a_filter_readiness_after_derivation.csv
07_25c10a_metric_derivation_gate_matrix.csv
08_25c10a_next_step_plan.csv
```

## Safety

CoreB remains blocked. No source recovery, mutation, live, final signal, Discord, MT5, AI, or live hook is allowed.

Expected status:

```text
COREB_UNIQUE_ORIGIN_METRIC_DERIVED_AUDIT_ONLY_FILTER_REPLAY_STILL_BLOCKED_PENDING_REVIEW
```

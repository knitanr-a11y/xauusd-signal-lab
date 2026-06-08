# GOLD V2 25C91 raw cluster parameter sweep audit-only spec

Created: 2026-06-08

Status: `RAW_CLUSTER_PARAMETER_SWEEP_SPEC_READY_AUDIT_ONLY`

## Purpose

25C88-25C90 showed that source-universe filters and rule tuples do not reconstruct CoreB top-ledger cluster membership. All variants effectively retain the 6834 RR125 raw universe.

25C91 performs one final raw-only reconstruction boundary test: parameterized clustering over raw RR125 rows.

## Cluster families

For each `dataset + direction` group:

1. `entry_gap_cluster`: start a new cluster if current entry_time - previous entry_time > gap.
2. `interval_gap_cluster`: start a new cluster if current entry_time > current_max_exit_time + gap.
3. `calendar_bucket_cluster`: group by fixed time buckets.

Gap/bucket candidates:

```text
5, 15, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440, 2880 minutes
```

## Match logic

For each CoreB top 125 row, attach the component that covers or is nearest to its entry time. Compare:

```text
component size vs same_count/source_rule_count
component unique origin count vs unique_origins
component profit aggregation vs top profit
```

## Inputs

```text
25c90_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

## Outputs

```text
GOLD_V2_25C91_RAW_CLUSTER_PARAMETER_SWEEP_AUDIT_ONLY_REPORT.md
25c91_summary.json
25c91_input_inventory.csv
25c91_cluster_parameter_sweep_summary.csv
25c91_cluster_parameter_sweep_rows.csv
25c91_best_candidate_matrix.csv
25c91_decision_matrix.csv
25c91_blocker_matrix.csv
```

## Success definition

A candidate is meaningful only if it reproduces all 125 rows for same_count/source_rule_count without A002.

Even if a candidate is found, it remains audit-only and requires human review before live.

## Guardrails

- No approximate match promotion.
- No source recovery approval.
- No A002 use.
- No live evaluator/final signal/external actions.

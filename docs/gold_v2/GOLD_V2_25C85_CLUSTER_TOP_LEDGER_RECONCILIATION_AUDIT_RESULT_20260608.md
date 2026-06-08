# GOLD V2 25C85 Cluster/top-ledger reconciliation audit result

Created UTC: 2026-06-08T08:25:54.579897+00:00

Status: `TOP_LEDGER_THRESHOLD_SUBSET_VALIDATED_CLUSTER_REPRESENTATIVE_LOGIC_BLOCKED`

## Purpose

Check whether `rr125_top_ledgers.csv` can be reconstructed from the exact OHLC/raw-rule universe produced in 25C84, and whether it explains the representative result for A002 events.

This is audit-only. It does not approve source recovery, live evaluator, final signal, Discord, MT5, or AI.

## Key result

```json
{
  "raw_rows": 16875,
  "top_rows": 2811,
  "top_base_rows_unique_non_filter": 471,
  "top_unique_entry_groups": 471,
  "top_a002_filter_rows": 404,
  "top_a002_unique_entries": 202,
  "official_a002_events": 772,
  "top_a002_overlap_with_official_a002": 137,
  "top_rows_failing_own_threshold": 0,
  "threshold_valid_rows_not_in_top": 2253,
  "same_count_equals_raw_rows_top_rows": 11,
  "unique_origins_equals_raw_unique_origins_top_rows": 286,
  "best_simple_profit_formula": "sum_raw",
  "best_simple_profit_formula_matches": 383,
  "a002_profit_binding_allowed": false
}
```

## What passed

Every row in `rr125_top_ledgers.csv` satisfies its own filter threshold when checked against its stored `same_count` and `unique_origins`.

This validates that top-ledger rows are internally threshold-consistent.

## What did not pass

### Full threshold expansion is too large

Unique non-filter top rows: 471.

If all known filters are applied to these rows based only on `same_count` and `unique_origins`, expected rows are 5064, but actual top rows are 2811.

Extra threshold-valid rows absent from top ledger: 2253.

Therefore, top-ledger is a curated/selected filter-output artifact, not a simple all-threshold expansion.

### same_count is not raw event row count

`same_count == raw rows grouped by dataset + entry_time + policy` only for 11 / 471 base top rows.

This confirms same_count is source-universe / cluster-count logic, not simple raw row count at the same timestamp.

### top-ledger is not full A002 source

For the two A002 filters:

```text
same_count>=2&unique_origins>=2
unique_origins>=2
```

Top-ledger contains:

```text
top A002 filter rows: 404
top A002 unique entry groups: 202
official A002 events: 772
overlap with official A002: 137
```

So `rr125_top_ledgers.csv` explains only part of the A002 event universe and cannot be used as the full 772-event result source.

### Representative profit is not a simple raw aggregation

Several simple formulas were tested against top-ledger `profit`:

- sum of raw profits at same event time
- mean / max / min / first / last raw profit
- same formulas restricted to top candidate id
- capped variants

Best simple formula was `sum_raw`, but it matched only 383 / 2811 top rows.

Therefore representative `profit` is not recovered by simple raw event aggregation.

## Conclusion

The top-ledger rows are threshold-valid, but the cluster/top representative generation logic remains unrecovered.

The missing source logic likely creates or selects:

- `cluster_id`
- `same_count`
- `source_rule_count`
- `top_candidate_id`
- representative `profit`
- a selected subset of threshold-valid filters

A002 event membership remains proven by 25C83/25C84, but A002 profit/PF/WR remains blocked.

## Recommended next step

`25C86_CLUSTER_REPRESENTATIVE_SOURCE_LOGIC_SEARCH_AUDIT_ONLY`

Search existing scripts/artifacts for the code or outputs that explicitly generate:

```text
rr125_top_ledgers.csv
cluster_id
same_count
source_rule_count
top_candidate_id
representative profit
```

Do not invent a representative selection rule.

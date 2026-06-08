# GOLD V2 25C86 Cluster representative source logic search audit result

Created UTC: 2026-06-08T08:34:33.614446+00:00

Status: `CLUSTER_REPRESENTATIVE_SOURCE_LOGIC_NOT_FOUND_AUDIT_ONLY_A002_MEMBERSHIP_PROVEN_PROFIT_BLOCKED`

## Purpose

Search for the original source logic that generated `rr125_top_ledgers.csv`, especially:

```text
cluster_id
same_count
source_rule_count
top_candidate_id
representative profit
```

This is audit-only. No source recovery approval, live evaluator, final signal, Discord, MT5, AI, or live hook is enabled.

## Summary

```json
{
  "raw_rule_universe_logic": "FOUND_AND_REPRODUCED",
  "cluster_representative_logic": "NOT_FOUND",
  "strict_original_candidate_found": false,
  "a002_membership_status": "PROVEN_EXACT",
  "a002_profit_status": "BLOCKED",
  "external_actions_allowed": false,
  "final_signal_allowed": false,
  "next_recommended_step": "REQUEST_ORIGINAL_CLUSTERING_SCRIPT_OR_MEMBERSHIP_LEDGER"
}
```

## Evidence

### Raw rule universe logic found

12E defines the raw rule universe by grouping `rr125_raw_signal_ledger.csv` over:

```text
candidate_id
origin_id
direction
variant
tp_pips
sl_pips
rr
rr_bucket
base_condition
added_filter_text
policy
```

and parses `base_condition` / `added_filter_text`. 25C82/25C84 then reproduced the raw row universe exactly from OHLC and these rule texts.

### Top-ledger representative logic not found

13C3 tried to reconstruct same_count and cluster membership from the raw ledger. It concluded that:

- `rr125_top_ledgers.csv` already stores source `cluster_id` / `same_count` / `source_rule_count`;
- `rr125_raw_signal_ledger.csv` has no row-level cluster membership;
- fixed entry-time windows and connected interval components do not reproduce source same_count;
- the original clustering algorithm or membership ledger is needed.

13C4/14D then searched/reviewed for a true original clustering generator. The strict criteria require a Python file that:

```text
reads raw RR125 signal ledger
assigns cluster_id
assigns same_count
constructs membership/grouping
writes or constructs top-ledger output
is not a generated audit/freeze helper
```

No currently supplied artifact satisfies that strict requirement.

### 25C85 confirms simple reconstruction is insufficient

25C85 showed:

```text
top_rows = 2811
top_base_rows_unique_non_filter = 471
threshold_valid_rows_not_in_top = 2253
best_simple_profit_formula = sum_raw
best_simple_profit_formula_matches = 383 / 2811
```

Therefore top-ledger representative profit is not a simple raw profit sum/mean/max/min/first/last or capped aggregation.

## Decision

| item | status | reason |
| --- | --- | --- |
| Raw RR125 rule universe | FOUND_AND_REPRODUCED | 25C84 exact raw row replay |
| A002 772 membership | PROVEN_EXACT | 25C83/25C84 zero-diff replay |
| Cluster representative source logic | NOT_FOUND | no original clustering/membership generator found |
| A002 profit / PF / WR | BLOCKED | representative raw row/profit selection missing |
| Approximate representative rule | FORBIDDEN | would be invented, not source-of-truth |

## Required next input

One of the following is needed:

```text
original RR125 top-ledger generation script
row-level cluster membership ledger
source row id mapping from raw rows to cluster_id/top-ledger representative
explicit representative profit selection rule used by the original search
```

## Recommended next step

`REQUEST_ORIGINAL_CLUSTERING_SCRIPT_OR_MEMBERSHIP_LEDGER`

If no such artifact exists, keep A002 as a proven audit-only event membership set but do not report A002 WR/PF.

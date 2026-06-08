# GOLD V2 25C84 Raw rule universe replay audit result

Created UTC: 2026-06-08T08:18:58.761008+00:00

Status: `RAW_RULE_AND_A002_REPLAY_EXACT_AUDIT_ONLY_PROFIT_BINDING_STILL_BLOCKED`

## Purpose

Validate, without assuming A002 is correct, whether the 33 raw RR125 rule texts can be applied to the uploaded OHLC-derived feature universe to regenerate:

1. the full `rr125_raw_signal_ledger.csv` row universe; and
2. the A002 772 event set.

This is audit-only. It does not approve source recovery, live evaluator, final signal, Discord, MT5, or AI use.

## Summary

```json
{
  "raw_rows": 16875,
  "generated_rows": 16875,
  "raw_unique_keys": 16875,
  "generated_unique_keys": 16875,
  "missing_raw_unique_keys": 0,
  "extra_generated_unique_keys": 0,
  "raw_rr1_event_groups": 3030,
  "generated_rr1_event_groups": 3030,
  "raw_a002_events": 772,
  "generated_a002_events": 772,
  "official_a002_events": 772,
  "generated_a002_missing_vs_official": 0,
  "official_a002_missing_from_generated": 0,
  "a002_event_replay_exact": true,
  "raw_row_replay_exact": true,
  "a002_profit_binding_allowed": false,
  "live_allowed": false,
  "final_signal_allowed": false
}
```

## Independent validation result

Using the OHLC-derived 38 features from 25C82 and the 33 raw RR125 rule texts, the audit regenerated the complete source universe:

| check | observed | expected | status |
| --- | ---: | ---: | --- |
| raw source rows | 16875 | 16875 | PASS |
| generated rows | 16875 | 16875 | PASS |
| missing raw rows | 0 | 0 | PASS |
| extra generated rows | 0 | 0 | PASS |
| RR1 event groups | 3030 | 3030 | PASS |
| generated A002 events | 772 | 772 | PASS |
| official A002 missing from generated | 0 | 0 | PASS |
| generated extra vs official A002 | 0 | 0 | PASS |

## Meaning

This is the strongest evidence so far that:

- the raw RR125 feature formulas are executable from OHLC;
- the 33 raw rule texts reproduce the raw source universe exactly;
- the A002 772 event set is not arbitrary and is not a broken artifact;
- A002 membership can be reproduced independently from OHLC + raw rule text + grouping rule.

## Still blocked

A002 profit/PF/WR use remains blocked.

Reason: A002 is an event-level grouping, while many events map to multiple raw rows. 25C79 showed only 56 of 772 events have a unique `profit_r + exit_time` under the tested keys; 716 remain ambiguous.

Therefore:

- A002 membership: `PROVEN_EXACT`
- raw row universe replay: `PROVEN_EXACT`
- raw outcome engine replay: `NEAR_EXACT` from 25C80
- A002 profit result assignment: `BLOCKED`
- live/final signal: `OFF`

## Next choices

### Option A: resolve representative result logic

Find or define the exact rule that maps each A002 event to one raw result row.

Needed examples:

```text
raw row id
or cluster representative row
or highest source_count / same_count representative
or top-ledger membership mapping
or deterministic representative selection rule already used by source exploration
```

### Option B: treat A002 as event membership only

Keep A002 as a reproducible event set but do not report WR/PF until representative result binding is solved.

### Option C: continue toward CoreB cluster/top-ledger reconciliation

Compare regenerated raw rows against `rr125_top_ledgers.csv` and reconstruct same_count / unique_origins / cluster_id behavior.

## Recommended next step

`25C85_REPRESENTATIVE_RESULT_BINDING_OR_CLUSTER_RECONCILIATION_AUDIT_ONLY`

The next audit should not recompute or invent performance. It should identify how the original source chose a representative trade result from multiple raw rows inside each A002 event.

# GOLD V2 25C83 A002 independent source validation

Created UTC: 2026-06-08T08:12:21.024195+00:00

Status: `A002_EVENT_SET_REPRODUCED_FROM_RAW_LEDGER_AUDIT_ONLY_PROFIT_BINDING_STILL_BLOCKED`

## Purpose

Validate A002 without assuming A002 is correct. The test starts from `rr125_raw_signal_ledger.csv`, applies a minimal audited grouping rule, and checks whether the A002 772 event set naturally reappears.

This does not approve source recovery, live evaluator, final signal, Discord, MT5, or AI use.

## Independent reproduction rule tested

```text
source = rr125_raw_signal_ledger.csv
policy = RR125_from_RR1_rules
group key = dataset + entry_time + policy
condition = unique_origins >= 2 AND raw_rows >= 2
time boundary = entry_time >= 2025-02-24 12:00:00
```

## Result

```json
{
  "a002_events": 772,
  "raw_rr1_rows": 6834,
  "raw_rr1_entry_groups": 3030,
  "raw_unique_origin_ge2_groups_all_dates": 866,
  "raw_unique_origin_ge2_groups_after_cutoff": 772,
  "a002_missing_from_raw_repro": 0,
  "raw_repro_extra_vs_a002": 0,
  "pre_cutoff_groups_excluded": 94,
  "top_unique_origins_filter_rows": 202,
  "top_same_count2_unique_filter_rows": 202,
  "top_unique_vs_a002_overlap": 137,
  "selected_source_count_raw_count_match_rows": 240,
  "selected_unique_origin_raw_match_rows": 1544,
  "a002_events_profit_exit_unique": 56,
  "a002_events_profit_exit_ambiguous": 716
}
```

## Evidence matrix

| claim | status | evidence |
| --- | --- | --- |
| A002 772 event set can be reproduced from raw ledger | PASS | RR1 raw ledger grouped by dataset+entry_time+policy, unique_origins>=2 and cutoff >= A002 min entry_time gives exactly 772 with zero set diff |
| A002 selected unique_origin_count values match raw ledger unique origin counts | PASS | 1544/1544 selected filter rows match |
| A002 source_count_by_entry_time equals raw row count | NOT_EQUAL | 240/1544 rows match; source_count appears to be source-universe/same_count style, not raw row count |
| rr125_top_ledgers filter rows are the source of A002 772 events | FAIL_AS_FULL_SOURCE | top ledger unique_origins>=2 has 202 rows, not 772 |
| A002 772 profit/exit can be assigned from raw ledger | BLOCKED | only 56/772 events have unique profit_r+exit_time |

## Interpretation

The A002 772 event set itself is reproduced exactly from the raw RR1 ledger with zero missing and zero extra rows after applying the A002 time boundary. This is strong evidence that A002 is not an arbitrary or broken event list.

However, A002 profit/result use remains blocked. Multiple raw rows still exist under many A002 event keys, and only 56 of 772 events have a unique `profit_r + exit_time` assignment.

## Important distinction

- A002 event membership: `PASS`
- A002 source_count numeric meaning: `PARTIAL`; unique origin counts match raw ledger, but source_count is not raw row count
- A002 profit/PF/WR from raw ledger: `BLOCKED`
- top-ledger as full A002 source: `FAIL_AS_FULL_SOURCE`, because top-ledger filter rows are 202, not 772

## Next

`25C84_RAW_RULE_UNIVERSE_REPLAY_OR_EXACT_A002_PROFIT_BINDING`

Recommended branch:

1. Continue raw-rule universe replay from OHLC to determine whether the 6834 RR1 raw rows can be regenerated.
2. Rebuild the A002 772 event set from regenerated raw rows.
3. Keep profit/PF/WR blocked until an exact representative raw-row rule is defined or recovered.

# GOLD V2 25C89 source-universe rule tuple membership audit-only spec

Created: 2026-06-08

Status: `SOURCE_UNIVERSE_RULE_TUPLE_MEMBERSHIP_SPEC_READY_AUDIT_ONLY`

## Purpose

25C88 filtered raw rows using independent value sets from `frozen_coreB_same_count_source_universe_20260604.json`. All tested filters still returned the same 6834 RR125 raw rows, so independent set filtering is too broad.

25C89 tests rule-level tuple membership instead.

## Hypothesis

CoreB source membership may be based on exact source-universe rule tuples, not on independent sets of candidate/origin/filter values.

Candidate tuple filters:

```text
added_filter_text
candidate_id + added_filter_text
origin_id + added_filter_text
variant + added_filter_text
candidate_id + variant + added_filter_text
origin_id + variant + added_filter_text
candidate_id + origin_id + variant + added_filter_text
```

Each raw row is considered a source-universe member only if it matches one full tuple from the frozen source universe.

For each tuple-membership subset, build interval connected components:

```text
group by dataset + direction
sort by entry_time
merge overlapping [entry_time, exit_time]
```

Then compare component covering each CoreB top row's entry_time against:

```text
top.same_count
top.source_rule_count
top.unique_origins
top.profit
```

## Inputs

```text
25c88_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
frozen_coreB_same_count_source_universe_20260604.json
```

## Outputs

```text
GOLD_V2_25C89_SOURCE_UNIVERSE_RULE_TUPLE_MEMBERSHIP_AUDIT_ONLY_REPORT.md
25c89_summary.json
25c89_input_inventory.csv
25c89_source_rule_tuple_inventory.csv
25c89_tuple_membership_reconstruction_summary.csv
25c89_tuple_membership_reconstruction_rows.csv
25c89_best_candidate_matrix.csv
25c89_decision_matrix.csv
25c89_blocker_matrix.csv
```

## Success definition

A candidate is meaningful only if it reproduces all 125 rows for `same_count` or `source_rule_count` without A002.

Even then, it remains audit-only and requires human review before live.

## Guardrails

- No approximate match promotion.
- No source recovery approval.
- No A002 use.
- No live evaluator/final signal/external actions.

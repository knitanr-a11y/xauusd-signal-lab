# GOLD V2 25C90 base-condition rule membership audit-only spec

Created: 2026-06-08

Status: `BASE_CONDITION_RULE_MEMBERSHIP_SPEC_READY_AUDIT_ONLY`

## Purpose

25C89 tested source-universe tuple membership using `candidate_id`, `origin_id`, `variant`, and `added_filter_text`, but all modes still behaved like the broad RR125 raw universe.

The missing key is likely `base_condition`.

`rr125_raw_signal_ledger.csv` has a `base_condition` column, while `frozen_coreB_same_count_source_universe_20260604.json` has `base_condition_objects` under each source rule. 25C90 reconstructs source membership using a normalized base-condition representation.

## Hypothesis

CoreB source membership may require matching a full rule predicate:

```text
base_condition + added_filter_text
```

not just the added filter or candidate/origin identifiers.

## Candidate tuple modes

```text
base_condition
base_condition + added_filter_text
base_condition + candidate_id + added_filter_text
base_condition + origin_id + added_filter_text
base_condition + variant + added_filter_text
base_condition + candidate_id + origin_id + variant + added_filter_text
```

For each mode, 25C90 tests two reconstruction styles:

1. Same-entry membership count.
2. Interval connected component membership count.

Both are compared against:

```text
top.same_count
top.source_rule_count
top.unique_origins
top.profit
```

## Inputs

```text
25c89_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
frozen_coreB_same_count_source_universe_20260604.json
```

## Outputs

```text
GOLD_V2_25C90_BASE_CONDITION_RULE_MEMBERSHIP_AUDIT_ONLY_REPORT.md
25c90_summary.json
25c90_input_inventory.csv
25c90_source_rule_base_condition_inventory.csv
25c90_reconstruction_summary.csv
25c90_reconstruction_rows.csv
25c90_best_candidate_matrix.csv
25c90_decision_matrix.csv
25c90_blocker_matrix.csv
```

## Success definition

A candidate is meaningful only if it reproduces all 125 rows for `same_count` or `source_rule_count` without A002.

Even then, it remains audit-only and requires human review before any live step.

## Guardrails

- No approximate match promotion.
- No source recovery approval.
- No A002 use.
- No live evaluator/final signal/external actions.

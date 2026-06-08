# GOLD V2 25C88 source-universe filtered component reconstruction audit-only spec

Created: 2026-06-08

Status: `SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_SPEC_READY_AUDIT_ONLY`

## Purpose

25C87 showed that `same_count` is not explained by individual condition-object hit counts or feature-time offsets.

The next likely source is cluster membership itself. Existing 13C3 code already tested raw interval connected components and found raw-all components insufficient. 25C88 extends this by filtering raw rows with the frozen same-count source universe before building interval components.

## Hypothesis

CoreB `same_count` may equal a component size after restricting `rr125_raw_signal_ledger.csv` to rows belonging to the frozen same-count source universe.

Candidate filters:

```text
all_rr125_raw_baseline
added_filter_text_in_source_universe
candidate_id_in_source_universe
origin_id_in_source_universe
variant_in_source_universe
candidate_or_origin_or_filter_in_source_universe
candidate_and_filter_in_source_universe
origin_and_filter_in_source_universe
```

For each filtered raw subset:

```text
group by dataset + direction
sort by entry_time
merge overlapping [entry_time, exit_time] intervals into connected components
```

Then compare component covering each CoreB top row's entry_time against:

```text
top.same_count
top.source_rule_count
top.unique_origins
top.profit using sum/mean/median/min/max/first/last
```

## Inputs

```text
25c87_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
frozen_coreB_same_count_source_universe_20260604.json
```

## Outputs

```text
GOLD_V2_25C88_SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_AUDIT_ONLY_REPORT.md
25c88_summary.json
25c88_input_inventory.csv
25c88_source_universe_identity_summary.csv
25c88_filtered_component_reconstruction_summary.csv
25c88_filtered_component_reconstruction_rows.csv
25c88_best_candidate_matrix.csv
25c88_decision_matrix.csv
25c88_blocker_matrix.csv
```

## Success definition

A candidate is meaningful only if it reproduces all 125 top rows for same_count/source_rule_count and does not rely on A002.

Even then, it remains audit-only and requires human review before live.

## Guardrails

- No approximate match promotion.
- No source recovery approval.
- No A002 use.
- No live evaluator/final signal/external actions.

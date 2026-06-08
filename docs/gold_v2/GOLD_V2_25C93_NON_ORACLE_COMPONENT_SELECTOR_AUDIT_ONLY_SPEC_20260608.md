# GOLD V2 25C93 non-oracle component selector audit-only spec

Created: 2026-06-08

Status: `NON_ORACLE_COMPONENT_SELECTOR_SPEC_READY_AUDIT_ONLY`

## Purpose

25C92 found an important boundary result:

```text
entry_gap=15m, nearby=0
same_count_oracle_exact=125/125
source_rule_count_oracle_exact=125/125
unique_origins_oracle_exact=125/125
```

This means the correct component exists among components covering each top-row entry time. However, the 25C92 oracle selected the correct component using the historical answer, so it is not deployable live logic.

25C93 tests non-oracle component selectors: rules that choose one component from the covering candidates without using target `same_count` / `source_rule_count`.

## Fixed component family

```text
family = entry_gap
gap_min = 15
nearby_min = 0
```

## Candidate selectors

For each CoreB top 125 row, build all components covering `entry_time` and test selectors such as:

```text
single_cover_if_only_one
smallest_count
largest_count
smallest_count_ge15
largest_count_ge15
max_unique_origins
min_unique_origins
latest_min_entry
earliest_min_entry
latest_max_exit
earliest_max_exit
shortest_duration
longest_duration
closest_min_entry
closest_center
max_profit_sum
min_profit_sum
max_profit_mean
min_profit_mean
contains_top_candidate_id_in_candidate_id
contains_top_candidate_id_in_origin_id
contains_entry_time_raw_row
contains_entry_time_and_top_candidate_id
```

## Match criteria

For each selector, compare the selected component against:

```text
same_count
source_rule_count
unique_origins
profit using sum/mean/median/min/max/first/last
```

## Inputs

```text
25c92_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

## Outputs

```text
GOLD_V2_25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY_REPORT.md
25c93_summary.json
25c93_input_inventory.csv
25c93_selector_summary.csv
25c93_selector_rows.csv
25c93_best_candidate_matrix.csv
25c93_decision_matrix.csv
25c93_blocker_matrix.csv
```

## Success definition

A selector candidate is meaningful only if it selects components matching all 125 rows for `same_count` or `source_rule_count` without using those target fields.

Even then, it remains audit-only and requires human review before live.

## Guardrails

- Oracle matching is not allowed in selector logic.
- No approximate match promotion.
- No source recovery approval.
- No A002 use.
- No live evaluator/final signal/external actions.

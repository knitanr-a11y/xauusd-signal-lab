# GOLD V2 25C94 non-oracle selector candidate review audit-only spec

Created: 2026-06-08

Status: `NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_SPEC_READY_AUDIT_ONLY`

## Purpose

25C93 found the first non-oracle CoreB count-field component selector candidate:

```text
component_family = entry_gap
gap_min = 15
selector = latest_start or closest_start
same_count_exact = 125 / 125
source_rule_count_exact = 125 / 125
unique_origins_exact = 125 / 125
profit_sum_exact = 0 / 125
```

25C94 reviews that candidate only. It must not restart broad count exploration. It must verify whether `latest_start` and `closest_start` are stable, whether they select the same component for every CoreB top row, and whether representative `profit` / `top_candidate_id` binding can be recovered without oracle logic.

25C94 does not approve source recovery and does not unlock live.

## Fixed source-of-truth inputs

The script must search the repo root and `FX_OUTPUTS` tree for these exact files:

```text
25c93_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

Required source semantics:

```text
raw source rows:
  file = rr125_raw_signal_ledger.csv
  filter = policy == RR125_from_RR1_rules
  expected_rows = 6834

top CoreB source rows:
  file = rr125_top_ledgers.csv
  filter = policy == RR125_from_RR1_rules AND filter == same_count>=15
  expected_rows = 125

direct historical CoreB SOT cross-check:
  file = gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
  expected_rows = 125 if present/usable
```

`gold_v2_13c_coreb_rr125_selected_top_ledgers.csv` is a historical SOT cross-check only. It must not be used to invent new live logic.

A002 is auxiliary-only and must not be used for CoreB metrics.

## Fixed reconstruction under review

25C94 must use the fixed reconstruction recovered by 25C93:

```text
component_family = entry_gap
gap_min = 15 minutes
selectors_under_review = latest_start, closest_start
```

For each `dataset + direction`, raw rows are sorted by `entry_time` / `exit_time`. A new component starts when the entry-time gap from the previous raw row is greater than 15 minutes. Covering components for a top row are components with:

```text
component_min_entry <= top.entry_time
component_max_exit >= top.entry_time
same dataset
same direction == top_direction
```

## Selector review checks

25C94 must evaluate both selectors independently and then compare them.

For every CoreB top row, output per-selector selected component fields:

```text
selector
dataset
entry_time
cluster_id
top_direction
top_candidate_id
top_profit
selected_component_id
component_min_entry
component_max_entry
component_max_exit
component_count
component_unique_origins
candidate_ids
origin_ids
contains_top_candidate_candidate
contains_top_candidate_origin
contains_top_candidate_any
same_count_match
source_rule_count_match
unique_origins_match
```

Then output a selector-pair stability matrix proving whether `latest_start` and `closest_start` choose the same component for all 125 rows.

Expected count result from 25C93:

```text
latest_start selected_rows = 125 / 125
latest_start same_count/source_rule_count/unique_origins = 125 / 125
closest_start selected_rows = 125 / 125
closest_start same_count/source_rule_count/unique_origins = 125 / 125
latest_start_vs_closest_start_same_component expected = 125 / 125
```

If any of these count/stability checks fail, stop as audit-only / live blocked. Do not attempt to promote profit binding.

## Representative profit / top_candidate_id binding checks

Within the selected component, test non-oracle representative selectors and profit aggregations. For each selector under review and each CoreB top row, compare the selected or aggregated raw `profit_r` against the top-row `profit`.

Required row selectors:

```text
candidate_id == top_candidate_id
origin_id == top_candidate_id
candidate_id == top_candidate_id OR origin_id == top_candidate_id
candidate_id contains top_candidate_id
origin_id contains top_candidate_id
candidate_id contains top_candidate_id OR origin_id contains top_candidate_id
earliest raw entry in selected component
latest raw entry in selected component
earliest raw exit in selected component
latest raw exit in selected component
max profit raw row
min profit raw row
first raw row by component sort order
last raw row by component sort order
```

Required aggregation selectors:

```text
sum profit_r
mean profit_r
median profit_r
min profit_r
max profit_r
first profit_r
last profit_r
```

Required diagnostics that must not be treated as deployable live logic by themselves:

```text
top_profit value from stored top row
top_profit existence among selected raw component rows
raw rows with profit_r equal to top profit
```

The top row's stored `profit` matching itself is expected and can support historical SOT reporting, but it is not a recovered raw-row representative binding.

## Outputs

25C94 must write these files under:

```text
Files/FX_OUTPUTS/gold_v2_25c94_non_oracle_selector_candidate_review_audit_only
```

Output files:

```text
GOLD_V2_25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
25c94_summary.json
25c94_input_inventory.csv
25c94_selector_component_rows.csv
25c94_selector_pair_stability.csv
25c94_profit_binding_summary.csv
25c94_profit_binding_rows.csv
25c94_profit_presence_diagnostics.csv
25c94_decision_matrix.csv
25c94_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c94_non_oracle_selector_candidate_review_audit_only.zip
```

## Success conditions

25C94 can only produce a candidate-ready status when all of the following are true:

```text
inputs_present = true
raw_rr125_rows = 6834
top125_rows = 125
25c93 status confirms candidate found
latest_start count fields = 125 / 125
closest_start count fields = 125 / 125
latest_start and closest_start same component = 125 / 125
at least one non-oracle raw-row or aggregation profit binding selector matches top profit = 125 / 125
```

Even when all conditions pass, live remains blocked and human review is required.

## Stop conditions

Stop as audit-only / live blocked when any of these occur:

```text
missing required input
raw/top row counts differ from expected source-of-truth counts
25c93 summary does not confirm the candidate status
latest_start / closest_start count fields fail
latest_start / closest_start select different components for any row
no non-oracle representative profit binding selector reaches 125 / 125
only stored top profit self-binding matches
```

## Status names

If inputs are missing or source counts are not usable:

```text
NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If selector count or selector stability review fails:

```text
NON_ORACLE_SELECTOR_COUNT_REVIEW_FAILED_AUDIT_ONLY_LIVE_BLOCKED
```

If count selector is confirmed but representative profit binding fails:

```text
NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
```

If count selector and representative profit binding both pass:

```text
NON_ORACLE_SELECTOR_AND_PROFIT_BINDING_CANDIDATE_READY_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

## Execution order

Run only this BAT for 25C94:

```text
scripts/gold_v2_runtime/bat/25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY.bat
```

It executes:

```text
python scripts\gold_v2_runtime\audit_gold_v2_25c94_non_oracle_selector_candidate_review_audit_only.py
```

No AI API, Discord, MT5, live hook, live evaluator, or final signal action is allowed.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- Oracle matching is not allowed in component selection or profit binding promotion.
- The stored top-row `profit` can be reported as historical SOT, but cannot by itself unlock live.
- No source recovery approval.
- No live evaluator/final signal/external actions.

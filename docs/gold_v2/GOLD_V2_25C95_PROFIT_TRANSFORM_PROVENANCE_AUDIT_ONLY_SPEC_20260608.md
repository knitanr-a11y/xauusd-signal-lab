# GOLD V2 25C95 profit transform provenance audit-only spec

Created: 2026-06-08

Status: `PROFIT_TRANSFORM_PROVENANCE_SPEC_READY_AUDIT_ONLY`

## Purpose

25C94 confirmed the non-oracle CoreB component selector for count fields, but representative profit binding remains blocked.

25C94 result:

```text
status = NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
component_family = entry_gap
gap_min = 15
latest_start_count_ok = true
closest_start_count_ok = true
latest_start_vs_closest_start_same_component = 125
direct profit binding = false
```

25C95 reviews whether the selected raw/component profit values from 25C94 can explain top-row `profit` through exact source-derived transforms. This is a post-25C94 audit. It is not source recovery approval and does not unlock live.

## Source-of-truth inputs

Use only the 25C94 output artifacts as input source-of-truth:

```text
25c94_summary.json
25c94_decision_matrix.csv
25c94_profit_binding_rows.csv
25c94_profit_binding_summary.csv
25c94_profit_presence_diagnostics.csv
25c94_selector_pair_stability.csv
```

The required 25C94 status is:

```text
NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
```

Expected rows:

```text
25c94_profit_binding_rows.csv rows = 5250
25c94_profit_binding_summary.csv rows = 42
25c94_selector_pair_stability.csv rows = 125
```

## Transform candidates

25C95 may test exact transforms only. It must not promote approximate matches.

Required transforms:

```text
direct = selected_profit
scale_3 = selected_profit * 3
scale_2 = selected_profit * 2
scale_4 = selected_profit * 4
scale_1_5 = selected_profit * 1.5
scale_0_75 = selected_profit * 0.75
scale_1_over_3 = selected_profit / 3
neg_direct = -selected_profit
neg_scale_3 = -selected_profit * 3
```

The `scale_3` candidate is included because 25C94 local artifacts showed partial exact alignment between raw-style profit levels and top-row profit levels. It remains a probe unless it reaches full 125/125 exact match and receives human review.

## Match criteria

For each `selector + binding_type + binding_method + transform`, compare:

```text
transformed_profit == top_profit
```

using exact numeric tolerance:

```text
abs(transformed_profit - top_profit) <= 1e-6
```

Required summary fields:

```text
selector
binding_type
binding_method
transform
rows
binding_found_rows
profit_match_rows
full_profit_match
```

Required row fields:

```text
top_row_index
selector
binding_type
binding_method
transform
entry_time
cluster_id
top_candidate_id
top_profit
selected_profit
transformed_profit
profit_match
selected_component_id
```

## Outputs

Write outputs to:

```text
Files/FX_OUTPUTS/gold_v2_25c95_profit_transform_provenance_audit_only
```

Output files:

```text
GOLD_V2_25C95_PROFIT_TRANSFORM_PROVENANCE_AUDIT_ONLY_REPORT.md
25c95_summary.json
25c95_input_inventory.csv
25c95_transform_summary.csv
25c95_transform_rows.csv
25c95_decision_matrix.csv
25c95_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c95_profit_transform_provenance_audit_only.zip
```

## Success condition

The strongest possible 25C95 result is still audit-only:

```text
PROFIT_TRANSFORM_BINDING_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

This requires at least one transform to match 125/125 rows for a non-oracle 25C94 binding method.

## Blocked condition

If no transform reaches 125/125:

```text
PROFIT_TRANSFORM_BINDING_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED
```

This means count selector recovery is preserved, but representative profit remains unresolved.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No AI API, Discord, MT5, live hook, live evaluator, or final signal.
- Partial transform matches must not be promoted.
- Stored top-row profit self-binding must not be treated as live-ready representative binding.

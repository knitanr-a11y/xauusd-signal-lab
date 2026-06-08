# GOLD V2 25C96 profit class mismatch diagnostic audit-only spec

Created: 2026-06-08

Status: `PROFIT_CLASS_MISMATCH_DIAGNOSTIC_SPEC_READY_AUDIT_ONLY`

## Purpose

25C95 confirmed that no exact profit transform reaches 125/125.

25C95 result:

```text
status = PROFIT_TRANSFORM_BINDING_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED
best_transform_profit_match_rows = 57 / 125
best candidates = max_profit_raw_row/profit_max with scale_3
```

25C96 is a diagnostic-only audit to explain why the best transform matches only part of the set. It must classify the 25C95 transform rows by top profit class, selected profit class, ratio, selector, binding method, and transform.

25C96 must not recover live logic, must not promote partial matches, and must not approve source recovery.

## Source-of-truth inputs

Use only local 25C95 and 25C94 output artifacts:

```text
25c95_summary.json
25c95_transform_rows.csv
25c95_transform_summary.csv
25c95_decision_matrix.csv
25c95_blocker_matrix.csv
25c94_summary.json
25c94_profit_binding_rows.csv
```

Required upstream status:

```text
25c95_summary.status = PROFIT_TRANSFORM_BINDING_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED
```

Expected counts:

```text
25c95_transform_rows.csv rows = 42750
25c95_transform_summary.csv rows = 342
25c94_profit_binding_rows.csv rows = 5250
```

## Required diagnostics

25C96 must output:

1. Best transform matrix from 25C95, sorted by `profit_match_rows`.
2. Top profit class distribution.
3. For each top profit class, the best matching transform/method.
4. For the known best candidates, class-level match/mismatch breakdown:

```text
selector in [latest_start, closest_start]
binding_method in [max_profit_raw_row, profit_max, candidate_id_eq_top_candidate_id]
transform = scale_3
```

5. Ratio diagnostics for direct selected profit rows:

```text
ratio = top_profit / selected_profit
rounded to 6 decimals
```

6. Mismatch rows for the best candidate:

```text
selector = latest_start
binding_method = max_profit_raw_row
transform = scale_3
```

The row-level mismatch output must include:

```text
top_row_index
entry_time
cluster_id
top_candidate_id
top_profit
selected_profit
transformed_profit
profit_match
selected_component_id
top_profit_class
selected_profit_class
ratio_class
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c96_profit_class_mismatch_diagnostic_audit_only
```

Output files:

```text
GOLD_V2_25C96_PROFIT_CLASS_MISMATCH_DIAGNOSTIC_AUDIT_ONLY_REPORT.md
25c96_summary.json
25c96_input_inventory.csv
25c96_top_profit_class_distribution.csv
25c96_best_by_top_profit_class.csv
25c96_focus_class_breakdown.csv
25c96_ratio_distribution.csv
25c96_best_candidate_mismatch_rows.csv
25c96_decision_matrix.csv
25c96_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c96_profit_class_mismatch_diagnostic_audit_only.zip
```

## Status names

If inputs are missing or expected upstream status/counts fail:

```text
PROFIT_CLASS_MISMATCH_DIAGNOSTIC_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If diagnostics are produced and no full transform is present:

```text
PROFIT_CLASS_MISMATCH_DIAGNOSTIC_READY_AUDIT_ONLY_LIVE_BLOCKED
```

If a full transform appears unexpectedly:

```text
PROFIT_CLASS_DIAGNOSTIC_UNEXPECTED_FULL_MATCH_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED
```

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not promote partial matches.
- Do not use top profit class as live logic.
- Do not treat ratio/class diagnostics as source recovery.

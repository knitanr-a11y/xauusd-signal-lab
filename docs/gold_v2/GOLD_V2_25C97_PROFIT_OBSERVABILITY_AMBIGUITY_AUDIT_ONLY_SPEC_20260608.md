# GOLD V2 25C97 profit observability ambiguity audit-only spec

Created: 2026-06-08

Status: `PROFIT_OBSERVABILITY_AMBIGUITY_SPEC_READY_AUDIT_ONLY`

## Purpose

25C96 showed that selected component count recovery is stable, but profit reconstruction is still blocked. Some profit classes are explainable by simple transforms, but no transform reaches 125/125.

25C96 facts:

```text
status = PROFIT_CLASS_MISMATCH_DIAGNOSTIC_READY_AUDIT_ONLY_LIVE_BLOCKED
best_transform_profit_match_rows = 57 / 125
top_profit_classes = 31
best_candidate_mismatch_rows = 68
```

25C97 tests whether the current non-oracle observed fields are sufficient to determine top-row `profit`, or whether the same observed signature maps to multiple top profit values. This is an ambiguity audit only.

## Source-of-truth inputs

Use local output artifacts only:

```text
25c96_summary.json
25c96_ratio_distribution.csv
25c96_focus_class_breakdown.csv
25c96_best_candidate_mismatch_rows.csv
25c94_summary.json
25c94_profit_binding_rows.csv
25c94_selector_component_rows.csv
```

Required upstream status:

```text
25c96_summary.status = PROFIT_CLASS_MISMATCH_DIAGNOSTIC_READY_AUDIT_ONLY_LIVE_BLOCKED
```

Expected rows:

```text
25c94_profit_binding_rows.csv rows = 5250
25c94_selector_component_rows.csv rows = 250
```

## Signature tests

Build one row per `top_row_index + selector` by pivoting 25C94 profit binding rows, then merge selected component fields from 25C94 selector component rows.

Classify numeric fields to 6 decimals.

Test these signature groups:

```text
extreme_no_id:
  selector, candidate_id_eq_top_candidate_id_class, max_profit_raw_row_class, min_profit_raw_row_class

extreme_with_top_candidate:
  selector, top_candidate_id, candidate_id_eq_top_candidate_id_class, max_profit_raw_row_class, min_profit_raw_row_class

shape_extreme:
  selector, component_count, component_unique_origins, candidate_id_eq_top_candidate_id_class, max_profit_raw_row_class, min_profit_raw_row_class

shape_extreme_with_candidate:
  selector, top_candidate_id, component_count, component_unique_origins, candidate_id_eq_top_candidate_id_class, max_profit_raw_row_class, min_profit_raw_row_class

full_observed_no_component_id:
  selector, top_candidate_id, component_count, component_unique_origins, candidate_ids, origin_ids,
  candidate_id_eq_top_candidate_id_class, max_profit_raw_row_class, min_profit_raw_row_class,
  first_component_sort_raw_row_class, last_component_sort_raw_row_class, profit_mean_class, profit_median_class
```

A collision exists when the same signature has more than one `top_profit_class`.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c97_profit_observability_ambiguity_audit_only
```

Output files:

```text
GOLD_V2_25C97_PROFIT_OBSERVABILITY_AMBIGUITY_AUDIT_ONLY_REPORT.md
25c97_summary.json
25c97_input_inventory.csv
25c97_observed_profit_feature_rows.csv
25c97_signature_summary.csv
25c97_signature_collision_groups.csv
25c97_signature_collision_rows.csv
25c97_decision_matrix.csv
25c97_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c97_profit_observability_ambiguity_audit_only.zip
```

## Status names

If inputs are missing or upstream status/counts fail:

```text
PROFIT_OBSERVABILITY_AMBIGUITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If collisions exist:

```text
PROFIT_OBSERVABILITY_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If every tested signature is unique:

```text
PROFIT_OBSERVABILITY_SIGNATURE_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even if signatures are unique historically, that is not live approval.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not use top profit classes as live logic.
- Do not promote historical signature uniqueness to source recovery.

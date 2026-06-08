# GOLD V2 25C98 temporal geometry profit collision audit-only spec

Created: 2026-06-08

Status: `TEMPORAL_GEOMETRY_PROFIT_COLLISION_SPEC_READY_AUDIT_ONLY`

## Purpose

25C97 proved that current non-oracle observed profit/component signatures are ambiguous: the same strict observed signature can map to multiple top-row `profit` values.

25C97 result:

```text
status = PROFIT_OBSERVABILITY_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED
signature_collision_groups = 48
strict_full_observed_collision_groups = 2
```

The strict collision pair shows identical observed component/profit classes but different top profit values:

```text
top_row_index 31: top_profit = 3.75
top_row_index 78: top_profit = 1.50
```

25C98 tests whether relative component temporal geometry resolves these collisions without using absolute dates as a rule.

This remains diagnostic audit-only. A temporal discriminator candidate is not source recovery approval and cannot unlock live.

## Source-of-truth inputs

Use local audit outputs only:

```text
25c97_summary.json
25c97_signature_collision_rows.csv
25c97_signature_collision_groups.csv
25c97_observed_profit_feature_rows.csv
25c94_selector_component_rows.csv
```

Required upstream status:

```text
25c97_summary.status = PROFIT_OBSERVABILITY_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

Expected rows:

```text
25c97_observed_profit_feature_rows.csv rows = 250
25c94_selector_component_rows.csv rows = 250
strict_full_observed_collision_groups = 2
```

## Temporal geometry fields

For each `top_row_index + selector`, merge selected component fields and compute relative values in minutes:

```text
entry_offset_from_component_min_min = entry_time - component_min_entry
component_entry_span_min = component_max_entry - component_min_entry
component_exit_span_min = component_max_exit - component_min_entry
component_tail_after_top_entry_min = component_max_exit - entry_time
component_entry_tail_after_top_entry_min = component_max_entry - entry_time
```

Also classify them to 6 decimals.

Absolute dates can be output for audit traceability, but the tested signatures must use relative geometry classes, not raw calendar timestamps.

## Signature tests

Re-test collision resolution using strict observed signatures plus temporal geometry:

```text
strict_plus_entry_offset:
  full_observed_no_component_id fields + entry_offset_from_component_min_min_class

strict_plus_entry_span:
  full_observed_no_component_id fields + component_entry_span_min_class

strict_plus_exit_span:
  full_observed_no_component_id fields + component_exit_span_min_class

strict_plus_all_geometry:
  full_observed_no_component_id fields + all temporal geometry classes
```

A collision remains if one signature has more than one `top_profit_class`.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c98_temporal_geometry_profit_collision_audit_only
```

Output files:

```text
GOLD_V2_25C98_TEMPORAL_GEOMETRY_PROFIT_COLLISION_AUDIT_ONLY_REPORT.md
25c98_summary.json
25c98_input_inventory.csv
25c98_temporal_feature_rows.csv
25c98_temporal_signature_summary.csv
25c98_temporal_collision_groups.csv
25c98_temporal_collision_rows.csv
25c98_strict_collision_temporal_rows.csv
25c98_decision_matrix.csv
25c98_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c98_temporal_geometry_profit_collision_audit_only.zip
```

## Status names

If inputs are missing or upstream status/counts fail:

```text
TEMPORAL_GEOMETRY_PROFIT_COLLISION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If strict collisions remain even after relative geometry:

```text
TEMPORAL_GEOMETRY_PROFIT_COLLISION_REMAINS_AUDIT_ONLY_LIVE_BLOCKED
```

If relative geometry resolves all tested strict collisions:

```text
TEMPORAL_GEOMETRY_PROFIT_COLLISION_RESOLVED_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even if resolved, this remains diagnostic only and cannot unlock live.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not use absolute calendar dates as live profit logic.
- Do not promote temporal uniqueness to source recovery.

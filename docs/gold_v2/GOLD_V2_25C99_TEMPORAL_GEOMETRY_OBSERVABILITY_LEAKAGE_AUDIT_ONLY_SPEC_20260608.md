# GOLD V2 25C99 temporal geometry observability leakage audit-only spec

Created: 2026-06-08

Status: `TEMPORAL_GEOMETRY_OBSERVABILITY_LEAKAGE_SPEC_READY_AUDIT_ONLY`

## Purpose

25C98 resolved the strict 25C97 profit collisions by adding relative temporal geometry. However, some geometry fields use `component_max_entry` or `component_max_exit`, which can be after the top-row `entry_time` and therefore may be future-looking at live entry time.

25C98 result:

```text
status = TEMPORAL_GEOMETRY_PROFIT_COLLISION_RESOLVED_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
temporal_signature_collision_groups = 0
strict_plus_all_geometry_collision_groups = 0
```

25C99 classifies which temporal geometry fields are observable at entry time and whether collision resolution depends on future-looking component geometry.

This is audit-only. It does not approve source recovery and does not unlock live.

## Source-of-truth inputs

Use local 25C98 output artifacts only:

```text
25c98_summary.json
25c98_temporal_feature_rows.csv
25c98_temporal_signature_summary.csv
25c98_strict_collision_temporal_rows.csv
25c98_decision_matrix.csv
25c98_blocker_matrix.csv
```

Required upstream status:

```text
25c98_summary.status = TEMPORAL_GEOMETRY_PROFIT_COLLISION_RESOLVED_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Expected rows:

```text
25c98_temporal_feature_rows.csv rows = 250
25c98_strict_collision_temporal_rows.csv rows = 4
```

## Field observability classification

Classify these fields:

```text
entry_offset_from_component_min_min:
  ex_ante_candidate if component_min_entry <= entry_time

component_entry_span_min:
  future_looking if component_max_entry > entry_time

component_exit_span_min:
  future_looking if component_max_exit > entry_time

component_tail_after_top_entry_min:
  future_looking if component_max_exit > entry_time

component_entry_tail_after_top_entry_min:
  future_looking if component_max_entry > entry_time
```

The script must count future-looking usage over all 250 feature rows and over the 4 strict collision rows.

## Ex-ante candidate signature test

Retest the 25C97 strict observed signature with only:

```text
entry_offset_from_component_min_min_class
```

Do not include `component_max_entry`, `component_max_exit`, exit span, tail, or absolute calendar timestamps in the ex-ante candidate signature.

If the entry-offset-only addition gives 0 collisions, it may be marked as an ex-ante disambiguator candidate for human review. It must not be promoted to live logic.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c99_temporal_geometry_observability_leakage_audit_only
```

Output files:

```text
GOLD_V2_25C99_TEMPORAL_GEOMETRY_OBSERVABILITY_LEAKAGE_AUDIT_ONLY_REPORT.md
25c99_summary.json
25c99_input_inventory.csv
25c99_temporal_field_observability.csv
25c99_row_observability_flags.csv
25c99_ex_ante_entry_offset_signature_summary.csv
25c99_ex_ante_entry_offset_collision_groups.csv
25c99_ex_ante_entry_offset_collision_rows.csv
25c99_strict_collision_observability_rows.csv
25c99_decision_matrix.csv
25c99_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c99_temporal_geometry_observability_leakage_audit_only.zip
```

## Status names

If inputs are missing or upstream status/counts fail:

```text
TEMPORAL_GEOMETRY_OBSERVABILITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If strict collision resolution requires future-looking geometry:

```text
TEMPORAL_GEOMETRY_RESOLUTION_REQUIRES_FUTURE_GEOMETRY_AUDIT_ONLY_LIVE_BLOCKED
```

If entry offset alone resolves tested strict collisions and all strict collision rows have `component_min_entry <= entry_time`:

```text
TEMPORAL_ENTRY_OFFSET_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even in the candidate status, source recovery remains blocked pending human review and independent provenance recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not use future component max entry/exit as live logic.
- Do not use absolute calendar dates as profit logic.
- Do not promote entry offset uniqueness to source recovery.

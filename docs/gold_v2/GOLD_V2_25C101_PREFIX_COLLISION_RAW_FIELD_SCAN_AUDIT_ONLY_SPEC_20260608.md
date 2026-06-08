# GOLD V2 25C101 prefix collision raw field scan audit-only spec

Created: 2026-06-08

Status: `PREFIX_COLLISION_RAW_FIELD_SCAN_SPEC_READY_AUDIT_ONLY`

## Purpose

25C100 invalidated the current entry-time prefix signature as a live-ready representative profit binding path.

25C100 result:

```text
status = ENTRY_TIME_PREFIX_SIGNATURE_AMBIGUOUS_AUDIT_ONLY_LIVE_BLOCKED
prefix_signature_collision_groups = 6
rows_with_future_component_rows = 232
all_full_strict_fields_equal_prefix = false
```

The 25C100 collision rows are all `top_profit = 1.50` versus `top_profit = 3.75` with prefix profit fields that are indistinguishable under the tested signature.

25C101 scans the raw RR125 ledger columns for entry-time prefix discriminators over only the 25C100 collision rows. It separates columns that are clearly future/outcome/profit fields from columns that may be ex-ante metadata. This is a discovery audit only and must not promote any discriminator to live logic.

## Source-of-truth inputs

Use local artifacts only:

```text
25c100_summary.json
25c100_prefix_feature_rows.csv
25c100_prefix_signature_collision_groups.csv
25c100_prefix_signature_collision_rows.csv
25c100_prefix_field_match_summary.csv
rr125_raw_signal_ledger.csv
```

Required upstream status:

```text
25c100_summary.status = ENTRY_TIME_PREFIX_SIGNATURE_AMBIGUOUS_AUDIT_ONLY_LIVE_BLOCKED
```

Expected counts:

```text
25c100_prefix_feature_rows.csv rows = 250
25c100_prefix_signature_collision_groups.csv rows = 6
25c100_prefix_signature_collision_rows.csv rows = 14
rr125_raw_signal_ledger.csv filtered RR125 rows = 6834
```

## Raw prefix scope

Filter raw rows:

```text
policy == RR125_from_RR1_rules
```

Reassign `entry_gap15` component IDs using the same audit-only logic as 25C100:

```text
sort by dataset, direction, entry_time, exit_time, candidate_id/origin_id
start a new component when entry_time gap > 15 minutes within same dataset+direction
component_id = dataset|direction|entry_gap15|component_number
```

For each 25C100 collision row, inspect prefix raw rows only:

```text
raw.selected_component_id == selected_component_id
raw.entry_time <= top.entry_time
```

## Column classification

Classify raw columns by name only into:

```text
forbidden_future_or_outcome:
  contains any of profit, pnl, outcome, result, win, loss, exit, close, tp, sl, mae, mfe, hit, duration, holding

structural_or_id:
  dataset, direction, candidate_id, origin_id, strategy_id, policy, filter, component, cluster, entry_time

candidate_ex_ante_review:
  all other columns
```

This name-based classification is conservative. Any resolving candidate from `candidate_ex_ante_review` still requires human review.

## Signature scan

For each raw column, aggregate prefix values per 25C100 collision row:

```text
prefix_<column>_value_set = sorted unique non-null values in prefix raw rows
```

Append this value set to the 25C100 prefix signature and count collisions.

Output one row per scanned column:

```text
raw_column
column_class
base_collision_groups
collision_groups_with_column
rows_in_collision_groups_with_column
max_top_profit_classes_with_column
resolves_collision
human_review_required
```

A resolving column means `collision_groups_with_column == 0`. It does not mean source recovery.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c101_prefix_collision_raw_field_scan_audit_only
```

Output files:

```text
GOLD_V2_25C101_PREFIX_COLLISION_RAW_FIELD_SCAN_AUDIT_ONLY_REPORT.md
25c101_summary.json
25c101_input_inventory.csv
25c101_raw_column_inventory.csv
25c101_collision_prefix_raw_value_rows.csv
25c101_raw_column_discriminator_summary.csv
25c101_resolving_column_candidates.csv
25c101_decision_matrix.csv
25c101_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c101_prefix_collision_raw_field_scan_audit_only.zip
```

## Status names

If inputs are missing or upstream status/counts fail:

```text
PREFIX_COLLISION_RAW_FIELD_SCAN_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If no entry-time raw column resolves the 25C100 collision rows:

```text
PREFIX_COLLISION_RAW_FIELD_SCAN_NO_EX_ANTE_DISCRIMINATOR_AUDIT_ONLY_LIVE_BLOCKED
```

If only forbidden future/outcome/profit columns resolve collisions:

```text
PREFIX_COLLISION_RAW_FIELD_SCAN_ONLY_FORBIDDEN_DISCRIMINATORS_AUDIT_ONLY_LIVE_BLOCKED
```

If one or more non-forbidden raw columns resolve the collision rows:

```text
PREFIX_COLLISION_RAW_FIELD_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even candidate status remains audit-only and does not approve source recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not use forbidden future/outcome/profit columns as live logic.
- Do not promote raw-column uniqueness to source recovery.

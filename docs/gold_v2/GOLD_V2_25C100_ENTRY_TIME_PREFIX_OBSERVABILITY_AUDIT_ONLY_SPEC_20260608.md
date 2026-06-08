# GOLD V2 25C100 entry-time prefix observability audit-only spec

Created: 2026-06-08

Status: `ENTRY_TIME_PREFIX_OBSERVABILITY_SPEC_READY_AUDIT_ONLY`

## Purpose

25C99 found an entry-offset disambiguator candidate:

```text
status = TEMPORAL_ENTRY_OFFSET_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
entry_offset_signature_collision_groups = 0
strict_rows_entry_offset_ex_ante = true
```

However, the strict signature still includes full-component fields such as component count, candidate set, profit aggregates, and first/last/max/min raw-row values. These fields may be calculated over the full selected component and can include rows after the top-row entry time.

25C100 audits whether the observed fields used with entry offset are available at entry time by recomputing prefix-only component features from the raw ledger.

This is audit-only. It does not approve source recovery and does not unlock live.

## Source-of-truth inputs

Use local artifacts only:

```text
25c99_summary.json
25c99_row_observability_flags.csv
25c99_ex_ante_entry_offset_signature_summary.csv
25c98_temporal_feature_rows.csv
25c94_selector_component_rows.csv
25c94_profit_binding_rows.csv
rr125_raw_signal_ledger.csv
```

Required upstream status:

```text
25c99_summary.status = TEMPORAL_ENTRY_OFFSET_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Expected counts:

```text
25c98_temporal_feature_rows.csv rows = 250
25c94_selector_component_rows.csv rows = 250
25c94_profit_binding_rows.csv rows = 5250
rr125_raw_signal_ledger.csv filtered RR125 rows = 6834
```

## Raw prefix reconstruction

Use only raw rows with:

```text
policy == RR125_from_RR1_rules
```

Reassign `entry_gap15` components exactly as prior audit-only scripts:

```text
sort by dataset, direction, entry_time, exit_time, candidate_id/origin_id
start new component when entry_time gap > 15 minutes within same dataset+direction
component_id = dataset|direction|entry_gap15|component_number
```

For each 25C98 feature row, locate its selected component and compute:

```text
full_component_raw_rows
prefix_component_raw_rows where raw.entry_time <= top.entry_time
future_component_raw_rows where raw.entry_time > top.entry_time
```

Compute prefix-only fields:

```text
prefix_component_count
prefix_component_unique_origins
prefix_candidate_ids
prefix_origin_ids
prefix_max_profit_raw_row
prefix_min_profit_raw_row
prefix_first_component_sort_raw_row
prefix_last_component_sort_raw_row
prefix_profit_mean
prefix_profit_median
prefix_profit_sum
```

Compare full observed fields vs prefix fields and mark whether each strict-signature field is entry-time observable.

## Prefix signature test

Build a prefix-only signature:

```text
selector
top_candidate_id
prefix_component_count
prefix_component_unique_origins
prefix_candidate_ids
prefix_origin_ids
prefix candidate_id_eq_top_candidate_id class
prefix max/min/first/last/mean/median profit classes
entry_offset_from_component_min_min_class
```

A collision exists if the same prefix-only signature maps to more than one top profit class.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c100_entry_time_prefix_observability_audit_only
```

Output files:

```text
GOLD_V2_25C100_ENTRY_TIME_PREFIX_OBSERVABILITY_AUDIT_ONLY_REPORT.md
25c100_summary.json
25c100_input_inventory.csv
25c100_prefix_feature_rows.csv
25c100_prefix_field_match_summary.csv
25c100_prefix_signature_summary.csv
25c100_prefix_signature_collision_groups.csv
25c100_prefix_signature_collision_rows.csv
25c100_strict_collision_prefix_rows.csv
25c100_decision_matrix.csv
25c100_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c100_entry_time_prefix_observability_audit_only.zip
```

## Status names

If inputs are missing or upstream status/counts fail:

```text
ENTRY_TIME_PREFIX_OBSERVABILITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If prefix-only signatures still collide:

```text
ENTRY_TIME_PREFIX_SIGNATURE_AMBIGUOUS_AUDIT_ONLY_LIVE_BLOCKED
```

If prefix-only signatures are unique but any full strict fields depend on future rows:

```text
ENTRY_TIME_PREFIX_DISAMBIGUATOR_CANDIDATE_FUTURE_FIELD_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED
```

If prefix-only signatures are unique and all required fields match prefix-only values:

```text
ENTRY_TIME_PREFIX_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even a candidate status remains audit-only and does not approve source recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not use full-component future rows as live logic.
- Do not promote prefix uniqueness to source recovery.

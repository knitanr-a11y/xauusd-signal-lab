# GOLD V2 25C102 non-ID discriminator full-set audit-only spec

Created: 2026-06-08

Status: `NON_ID_DISCRIMINATOR_FULL_SET_SPEC_READY_AUDIT_ONLY`

## Purpose

25C101 found raw prefix columns that resolve the 25C100 collision subset:

```text
status = PREFIX_COLLISION_RAW_FIELD_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
resolving_raw_columns = 7
non_forbidden_resolving_raw_columns = 6
```

The resolving columns include calendar/identity-like columns:

```text
entry_month
entry_time
selected_component_id
```

and review candidates:

```text
entry_price
train_score
added_filter_text
```

25C102 tests whether the non-ID review candidates still resolve profit ambiguity over the full 250 feature rows, and separates exact/high-cardinality fields from potentially meaningful rule/score fields.

This is audit-only. It does not approve source recovery and does not unlock live.

## Source-of-truth inputs

Use local artifacts only:

```text
25c101_summary.json
25c101_resolving_column_candidates.csv
25c101_raw_column_discriminator_summary.csv
25c101_collision_prefix_raw_value_rows.csv
25c100_prefix_feature_rows.csv
rr125_raw_signal_ledger.csv
```

Required upstream status:

```text
25c101_summary.status = PREFIX_COLLISION_RAW_FIELD_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Expected counts:

```text
25c100_prefix_feature_rows.csv rows = 250
rr125_raw_signal_ledger.csv filtered RR125 rows = 6834
25c101 resolving columns >= 7
```

## Candidate classes

Hard-reject for live promotion:

```text
entry_time
entry_month
selected_component_id
exit_time
```

Review-only candidates:

```text
added_filter_text
train_score
entry_price
```

`entry_price` exact values are treated as high-cardinality/likely overfit unless a coarse rounded/bin version also resolves.

`train_score` exact value sets are treated as review-only unless coarser aggregates also resolve.

`added_filter_text` exact value set is review-only and must be inspected because it may represent the source rule/filter identity rather than a price/time identifier.

## Full-set discriminator tests

For all 250 prefix feature rows, aggregate raw prefix values for each candidate column:

```text
raw.selected_component_id == selected_component_id
raw.entry_time <= top.entry_time
```

Append each candidate representation to the 25C100 prefix signature and count full-set collisions.

Representations:

```text
added_filter_text_value_set
added_filter_text_count
added_filter_text_token_set
train_score_value_set
train_score_count
train_score_min_class
train_score_max_class
train_score_mean_class
entry_price_value_set
entry_price_round_1
entry_price_round_5
entry_price_round_10
entry_month_value_set
entry_time_value_set
selected_component_id_value_set
exit_time_value_set
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c102_non_id_discriminator_full_set_audit_only
```

Output files:

```text
GOLD_V2_25C102_NON_ID_DISCRIMINATOR_FULL_SET_AUDIT_ONLY_REPORT.md
25c102_summary.json
25c102_input_inventory.csv
25c102_candidate_feature_rows.csv
25c102_candidate_discriminator_summary.csv
25c102_candidate_collision_groups.csv
25c102_candidate_collision_rows.csv
25c102_decision_matrix.csv
25c102_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c102_non_id_discriminator_full_set_audit_only.zip
```

## Status names

If inputs are missing or upstream/count checks fail:

```text
NON_ID_DISCRIMINATOR_FULL_SET_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If only hard-reject columns resolve the full set:

```text
NON_ID_DISCRIMINATOR_FULL_SET_ONLY_ID_OR_FORBIDDEN_AUDIT_ONLY_LIVE_BLOCKED
```

If no representation resolves the full set:

```text
NON_ID_DISCRIMINATOR_FULL_SET_UNRESOLVED_AUDIT_ONLY_LIVE_BLOCKED
```

If one or more review-only non-ID representations resolve the full set:

```text
NON_ID_DISCRIMINATOR_FULL_SET_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even candidate status remains audit-only and does not approve source recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not use calendar/time/component identifiers as live profit logic.
- Do not use forbidden future/outcome/profit fields as live logic.
- Do not promote non-ID discriminator uniqueness to source recovery.

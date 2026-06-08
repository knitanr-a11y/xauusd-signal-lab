# GOLD V2 25C104 rule-text temporal holdout audit-only spec

Created: 2026-06-08

Status: `RULE_TEXT_TEMPORAL_HOLDOUT_SPEC_READY_AUDIT_ONLY`

## Purpose

25C103 found reduced rule-text representations that resolve full-set collisions when appended to the 25C100 prefix signature:

```text
status = RULE_TEXT_REDUCED_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
rule_text_reduced_resolving = 3
```

The strongest low-cardinality candidate is:

```text
filter_family_set
unique_values = 28
unique_ratio = 0.112
collision_groups = 0
```

However, when appended to the long prefix signature, the resulting key may still be near-unique historical memorization rather than a reusable profit binding rule.

25C104 audits temporal holdout coverage and key reuse. This is audit-only and cannot unlock live.

## Source-of-truth inputs

Use local artifacts only:

```text
25c103_summary.json
25c103_reduced_feature_rows.csv
25c103_reduced_discriminator_summary.csv
25c103_decision_matrix.csv
25c103_blocker_matrix.csv
```

Required upstream status:

```text
25c103_summary.status = RULE_TEXT_REDUCED_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Expected counts:

```text
25c103_reduced_feature_rows.csv rows = 250
25c103_reduced_discriminator_summary.csv rows = 14
```

## Candidate keys

Test these keys:

```text
prefix_only
prefix_plus_filter_family_set
prefix_plus_filter_feature_name_set
prefix_plus_filter_operator_feature_set
selector_top_candidate_filter_family_only
```

Where `prefix_only` is the 25C100 prefix signature:

```text
selector
top_candidate_id
prefix_component_count
prefix_component_unique_origins
prefix_candidate_ids
prefix_origin_ids
prefix_candidate_id_eq_top_candidate_id_class
prefix_max_profit_raw_row_class
prefix_min_profit_raw_row_class
prefix_first_component_sort_raw_row_class
prefix_last_component_sort_raw_row_class
prefix_profit_mean_class
prefix_profit_median_class
entry_offset_from_component_min_min_class
```

## Full-set collision and cardinality metrics

For each key, compute:

```text
groups
collision_groups
rows_in_collision_groups
max_top_profit_classes
unique_ratio = groups / 250
```

## Temporal holdout test

For each key, do leave-one-entry-month-out testing:

1. Train on all months except one.
2. Build a map from key -> top_profit_class if the training key maps to exactly one top_profit_class.
3. For the held-out month, count:
   - test_rows
   - seen_key_rows
   - unseen_key_rows
   - conflicted_train_key_rows
   - correct_seen_rows
   - seen_coverage = seen_key_rows / test_rows
   - seen_accuracy = correct_seen_rows / seen_key_rows

Also aggregate over all held-out months.

A candidate with full-set collision zero but very low seen coverage is historical-disambiguating only and must remain blocked.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c104_rule_text_temporal_holdout_audit_only
```

Output files:

```text
GOLD_V2_25C104_RULE_TEXT_TEMPORAL_HOLDOUT_AUDIT_ONLY_REPORT.md
25c104_summary.json
25c104_input_inventory.csv
25c104_key_collision_cardinality_summary.csv
25c104_month_holdout_detail.csv
25c104_holdout_aggregate.csv
25c104_decision_matrix.csv
25c104_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c104_rule_text_temporal_holdout_audit_only.zip
```

## Status names

If inputs are missing or upstream/count checks fail:

```text
RULE_TEXT_TEMPORAL_HOLDOUT_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If the best rule-text key has full-set collision zero but aggregate seen coverage is below 0.50:

```text
RULE_TEXT_TEMPORAL_HOLDOUT_COVERAGE_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
```

If the best rule-text key has full-set collision zero, aggregate seen coverage >= 0.50, and seen accuracy >= 0.95:

```text
RULE_TEXT_TEMPORAL_HOLDOUT_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

If no rule-text key remains collision-free:

```text
RULE_TEXT_TEMPORAL_HOLDOUT_UNRESOLVED_AUDIT_ONLY_LIVE_BLOCKED
```

Even candidate status remains audit-only and does not approve source recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not promote historical key uniqueness to source recovery.
- Do not unlock CoreB live evaluator.

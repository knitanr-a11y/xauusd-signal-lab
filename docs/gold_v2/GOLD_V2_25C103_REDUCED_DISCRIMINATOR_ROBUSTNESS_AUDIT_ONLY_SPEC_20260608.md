# GOLD V2 25C103 reduced discriminator robustness audit-only spec

Created: 2026-06-08

Status: `REDUCED_DISCRIMINATOR_ROBUSTNESS_SPEC_READY_AUDIT_ONLY`

## Purpose

25C102 found full-set resolving non-ID representations, but several candidates are exact/high-cardinality or may encode time/price/regime identity rather than a recoverable source rule.

25C102 result:

```text
status = NON_ID_DISCRIMINATOR_FULL_SET_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
full_set_resolving_representations = 12
review_only_non_id_resolving_representations = 8
hard_reject_resolving_representations = 4
```

Resolving review-only candidates include:

```text
added_filter_text_value_set
added_filter_text_token_set
train_score_value_set
train_score_mean_class
entry_price_value_set
entry_price_round_1/5/10
```

25C103 tests whether reduced, lower-cardinality forms also resolve ambiguity:

- source-rule style forms from `added_filter_text`
- score-bin forms from `train_score`
- coarse price-regime forms from `entry_price`

This is audit-only. It does not approve source recovery and does not unlock live.

## Source-of-truth inputs

Use local artifacts only:

```text
25c102_summary.json
25c102_candidate_feature_rows.csv
25c102_candidate_discriminator_summary.csv
25c102_candidate_collision_groups.csv
25c102_candidate_collision_rows.csv
```

Required upstream status:

```text
25c102_summary.status = NON_ID_DISCRIMINATOR_FULL_SET_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Expected counts:

```text
25c102_candidate_feature_rows.csv rows = 250
25c102_candidate_discriminator_summary.csv rows = 16
```

## Reduced representations

From `added_filter_text_value_set` derive:

```text
filter_feature_name_set
filter_operator_feature_set
filter_family_set
filter_family_count
filter_condition_count
```

Feature name extraction:

```text
condition: <feature> <operator> <threshold>
operators: <=, >=, >, <, ==
feature = left-hand side stripped of whitespace
```

Family mapping:

```text
m5_* -> m5
contains compression -> compression
contains range -> range
contains dist_low -> dist_low
contains dist_high -> dist_high
contains abs_ret -> abs_ret
contains ret -> ret
contains wick -> wick
else first token before underscore
```

From `train_score` derive:

```text
train_score_mean_bin_0_1
train_score_mean_bin_0_25
train_score_mean_bin_0_5
train_score_range_bin_0_25
train_score_count
```

From `entry_price` derive coarse price-regime review-only fields:

```text
entry_price_bin_25
entry_price_bin_50
entry_price_bin_100
entry_price_bin_250
```

Price-regime fields may be useful diagnostics but must not be promoted as source recovery.

## Collision test

For each reduced representation, append it to the 25C100 prefix signature and count collisions over all 250 rows.

A representation resolves the ambiguity if:

```text
collision_groups == 0
```

Also record cardinality:

```text
unique_values
unique_ratio = unique_values / 250
```

Exact/high-cardinality representations remain suspect even when they resolve.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c103_reduced_discriminator_robustness_audit_only
```

Output files:

```text
GOLD_V2_25C103_REDUCED_DISCRIMINATOR_ROBUSTNESS_AUDIT_ONLY_REPORT.md
25c103_summary.json
25c103_input_inventory.csv
25c103_reduced_feature_rows.csv
25c103_reduced_discriminator_summary.csv
25c103_reduced_collision_groups.csv
25c103_reduced_collision_rows.csv
25c103_decision_matrix.csv
25c103_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c103_reduced_discriminator_robustness_audit_only.zip
```

## Status names

If inputs are missing or upstream/count checks fail:

```text
REDUCED_DISCRIMINATOR_ROBUSTNESS_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If any reduced rule-text representation resolves the full set:

```text
RULE_TEXT_REDUCED_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

If no reduced rule-text representation resolves but a train-score bin resolves:

```text
TRAIN_SCORE_BIN_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

If only coarse price-regime fields resolve:

```text
PRICE_REGIME_ONLY_DISCRIMINATOR_AUDIT_ONLY_LIVE_BLOCKED
```

If none of the reduced forms resolve:

```text
REDUCED_DISCRIMINATOR_FORMS_UNRESOLVED_AUDIT_ONLY_LIVE_BLOCKED
```

Even candidate status remains audit-only and does not approve source recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not promote exact text/score/price uniqueness to source recovery.
- Do not use price regime as live profit binding without independent approval.
- Do not unlock CoreB live evaluator.

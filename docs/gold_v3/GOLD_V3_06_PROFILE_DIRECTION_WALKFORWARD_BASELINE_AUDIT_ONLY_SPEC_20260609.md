# GOLD V3 06 profile-direction walk-forward baseline audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_06_PROFILE_DIRECTION_WALKFORWARD_BASELINE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 06 creates lightweight profile-direction baseline diagnostics from the 05 joined label/feature dataset and the 05 walk-forward fold matrix.

The goal is to avoid uploading or reviewing the large 05 joined CSV while still checking whether each TP/SL profile and direction has stable walk-forward behavior.

This step does not select candidates, optimize thresholds, train models, generate signals, call APIs, or create ZIP output.

## Required upstream

```text
GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_summary.json
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_label_feature_join_rows.csv
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_walkforward_fold_matrix.csv
```

Only a small set of label columns is read from the large joined file:

```text
entry_month
profile_id
direction
label_outcome
label_price_distance_result_usd
```

## Computation

For every walk-forward fold and for each split:

```text
train
validation
test
```

Group by:

```text
profile_id
direction
```

Compute:

```text
rows
tp_count
sl_count
timeout_count
other_count
tp_rate
sl_rate
timeout_rate
avg_result_usd
sum_result_usd
positive_avg_result
```

Then aggregate test split behavior across folds:

```text
test_folds
test_positive_folds
test_positive_fold_rate
test_avg_result_mean
test_avg_result_min
test_avg_result_max
test_sum_result_total
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/06_profile_direction_walkforward_baseline_audit_only/
```

Output files:

```text
GOLD_V3_06_PROFILE_DIRECTION_WALKFORWARD_BASELINE_AUDIT_ONLY_REPORT.md
gold_v3_06_summary.json
gold_v3_06_input_inventory.csv
gold_v3_06_fold_split_profile_direction_baseline.csv
gold_v3_06_profile_direction_test_stability_summary.csv
gold_v3_06_month_profile_direction_summary.csv
gold_v3_06_decision_matrix.csv
gold_v3_06_blocker_matrix.csv
```

ZIP output is disabled.

## Status names

```text
GOLD_V3_06_PROFILE_DIRECTION_BASELINE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
GOLD_V3_06_PROFILE_DIRECTION_BASELINE_BLOCKED_AUDIT_ONLY
GOLD_V3_06_PROFILE_DIRECTION_BASELINE_READY_AUDIT_ONLY
```

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- No candidate selection.
- No threshold optimization.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

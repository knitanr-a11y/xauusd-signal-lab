# GOLD V3 07 feature bucket lift scan audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_07_FEATURE_BUCKET_LIFT_SCAN_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 07 scans entry-time features with walk-forward discipline to find whether simple feature buckets improve profile-direction results.

This is still audit-only exploratory scanning. It does not finalize candidates, optimize live thresholds, train models, generate signals, or call external actions.

## Required upstream

```text
GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY
GOLD_V3_06_PROFILE_DIRECTION_BASELINE_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_summary.json
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_label_feature_join_rows.csv
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_feature_column_inventory.csv
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_walkforward_fold_matrix.csv
Files/FX_OUTPUTS/gold_v3/06_profile_direction_walkforward_baseline_audit_only/gold_v3_06_summary.json
```

## Scan design

For each fold, profile, direction, and numeric feature:

1. Use train rows only to create five quantile buckets.
2. Score buckets on validation rows.
3. Pick the validation-best bucket for that fold/profile/direction/feature.
4. Report its test result.

Test data must not be used to choose a bucket.

## Minimum rows

A bucket is usable only if it has enough validation/test rows.

```text
min_validation_rows = 50
min_test_rows = 50
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/07_feature_bucket_lift_scan_audit_only/
```

Output files:

```text
GOLD_V3_07_FEATURE_BUCKET_LIFT_SCAN_AUDIT_ONLY_REPORT.md
gold_v3_07_summary.json
gold_v3_07_input_inventory.csv
gold_v3_07_feature_scan_inventory.csv
gold_v3_07_fold_feature_bucket_scan.csv
gold_v3_07_feature_bucket_test_stability_summary.csv
gold_v3_07_top_feature_bucket_candidates.csv
gold_v3_07_decision_matrix.csv
gold_v3_07_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- Train defines bucket edges.
- Validation chooses bucket.
- Test only reports result.
- No final candidate approval.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

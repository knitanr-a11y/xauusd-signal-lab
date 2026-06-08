# GOLD V3 08 bucket boundary provenance audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 07 found strong feature bucket lift rows, but B1/B2/B3/B4/B5 labels are not sufficient for reproducible rule review unless the underlying train-defined bucket boundaries are persisted.

GOLD V3 08 recomputes the exact fold-specific bucket boundaries using the same rule as 07 and writes them as audit artifacts.

This step does not approve candidates, train models, generate signals, call APIs, or create ZIP output.

## Required upstream

```text
GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY
GOLD_V3_07_FEATURE_BUCKET_SCAN_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_summary.json
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_label_feature_join_rows.csv
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_walkforward_fold_matrix.csv
Files/FX_OUTPUTS/gold_v3/07_feature_bucket_lift_scan_audit_only/gold_v3_07_summary.json
Files/FX_OUTPUTS/gold_v3/07_feature_bucket_lift_scan_audit_only/gold_v3_07_top_feature_bucket_candidates.csv
Files/FX_OUTPUTS/gold_v3/07_feature_bucket_lift_scan_audit_only/gold_v3_07_fold_feature_bucket_scan.csv
```

## Boundary rule

For each selected fold/profile/direction/feature row:

1. Read train months from the 05 fold matrix.
2. Filter train rows by profile_id and direction.
3. Compute 0/20/40/60/80/100 percent quantile boundaries of the feature value.
4. Remove duplicate boundaries.
5. Convert selected bucket B1..B5 into its lower/upper edge.

Boundary inclusivity follows pandas cut behavior from 07:

```text
include_lowest = true
first lower edge = -inf
last upper edge = +inf
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/
```

Output files:

```text
GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_AUDIT_ONLY_REPORT.md
gold_v3_08_summary.json
gold_v3_08_input_inventory.csv
gold_v3_08_selected_bucket_boundary_rows.csv
gold_v3_08_boundary_stability_summary.csv
gold_v3_08_decision_matrix.csv
gold_v3_08_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- Recompute boundaries from train rows only.
- Do not use test data to define boundaries.
- No final candidate approval.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

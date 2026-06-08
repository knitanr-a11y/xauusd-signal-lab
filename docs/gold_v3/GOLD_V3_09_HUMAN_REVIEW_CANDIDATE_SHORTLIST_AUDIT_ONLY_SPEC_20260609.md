# GOLD V3 09 human review candidate shortlist audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 09 converts GOLD V3 07/08 audit artifacts into a human-review candidate shortlist.

This is not final approval. It only prepares a compact review matrix that shows which profile/direction/feature bucket families deserve deeper inspection.

## Required upstream

```text
GOLD_V3_07_FEATURE_BUCKET_SCAN_READY_AUDIT_ONLY
GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/07_feature_bucket_lift_scan_audit_only/gold_v3_07_summary.json
Files/FX_OUTPUTS/gold_v3/07_feature_bucket_lift_scan_audit_only/gold_v3_07_feature_bucket_test_stability_summary.csv
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/gold_v3_08_summary.json
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/gold_v3_08_boundary_stability_summary.csv
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/gold_v3_08_selected_bucket_boundary_rows.csv
```

## Review filter

Default human-review shortlist filter:

```text
folds >= 6
positive_test_fold_rate >= 0.8
test_avg_result_mean > 0
test_lift_mean > 0
test_rows_total >= 3000
all_boundaries_valid = true
```

Rows not passing this filter remain in diagnostic outputs but are not placed into the primary shortlist.

## Ranking

A non-live review score is computed for sorting only:

```text
review_score =
  positive_test_fold_rate * 100
  + test_lift_mean * 10
  + test_avg_result_mean
  + log10(test_rows_total + 1)
```

This score is not a live signal and must not be used for trading.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/09_human_review_candidate_shortlist_audit_only/
```

Output files:

```text
GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_AUDIT_ONLY_REPORT.md
gold_v3_09_summary.json
gold_v3_09_input_inventory.csv
gold_v3_09_human_review_candidate_shortlist.csv
gold_v3_09_rejected_candidate_diagnostics.csv
gold_v3_09_boundary_preview_rows.csv
gold_v3_09_decision_matrix.csv
gold_v3_09_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- This is a review shortlist only.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

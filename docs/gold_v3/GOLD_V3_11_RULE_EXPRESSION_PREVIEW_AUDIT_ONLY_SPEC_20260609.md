# GOLD V3 11 rule expression preview audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_11_RULE_EXPRESSION_PREVIEW_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 11 converts GOLD V3 10 review cards and the full GOLD V3 08 fold-level boundary provenance into human-readable rule expression previews.

This step is still audit-only. It does not approve final candidates, finalize thresholds, train models, generate signals, or call external actions.

## Required upstream

```text
GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_READY_AUDIT_ONLY
GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/10_candidate_family_review_card_audit_only/gold_v3_10_summary.json
Files/FX_OUTPUTS/gold_v3/10_candidate_family_review_card_audit_only/gold_v3_10_candidate_family_review_rows.csv
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/gold_v3_08_summary.json
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/gold_v3_08_selected_bucket_boundary_rows.csv
```

Do not use `gold_v3_10_boundary_card_rows.csv` as the only boundary source because it is representative-card scoped and does not cover every 10 candidate row.

## Rule expression preview

For each candidate review row:

1. Read all matching fold-level boundary rows from GOLD V3 08.
2. Determine the dominant bucket id across folds.
3. Compute the dominant bucket rate.
4. Build the preview expression from only the dominant-bucket subset.
5. Determine the dominant threshold type:

```text
lower_bound: feature >= threshold
upper_bound: feature <= threshold
range:       lower <= feature <= upper
missing:     no boundary rows
mixed:       no stable preview expression
```

6. Use median fold boundary values only for preview.

The preview expression is not a finalized live rule.

## Readiness labels

```text
REVIEW_READY
REVIEW_READY_WITH_NEGATIVE_FOLD_RISK
MANUAL_REVIEW_BUCKET_UNSTABLE
MANUAL_REVIEW_BOUNDARY_UNSTABLE
MANUAL_REVIEW_BOUNDARY_MISSING
REVIEW_ONLY_NOT_DEPLOYABLE_RAW_PRICE_LEVEL
```

Raw price-level EMA candidates remain review-only due stationarity risk.

Default dominant bucket stability threshold:

```text
dominant_bucket_rate >= 0.60
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/11_rule_expression_preview_audit_only/
```

Output files:

```text
GOLD_V3_11_RULE_EXPRESSION_PREVIEW_AUDIT_ONLY_REPORT.md
gold_v3_11_summary.json
gold_v3_11_input_inventory.csv
gold_v3_11_rule_expression_preview_rows.csv
gold_v3_11_feature_family_readiness_summary.csv
gold_v3_11_boundary_consensus_diagnostics.csv
gold_v3_11_decision_matrix.csv
gold_v3_11_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- Preview expressions only.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

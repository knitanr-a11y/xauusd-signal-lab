# GOLD V3 10 candidate family review card audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 10 converts the strict-boundary GOLD V3 09 human review shortlist into feature-family review cards.

The goal is to reduce duplicate-looking candidates and expose feature-family risks before any final human decision.

This is not final approval. It does not finalize thresholds, train models, generate signals, or call external actions.

## Required upstream

```text
GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_READY_AUDIT_ONLY
```

The upstream shortlist must also report:

```text
shortlist_boundary_strict_valid = true
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/09_human_review_candidate_shortlist_audit_only/gold_v3_09_summary.json
Files/FX_OUTPUTS/gold_v3/09_human_review_candidate_shortlist_audit_only/gold_v3_09_human_review_candidate_shortlist.csv
Files/FX_OUTPUTS/gold_v3/08_bucket_boundary_provenance_audit_only/gold_v3_08_selected_bucket_boundary_rows.csv
```

## Feature family classification

Each feature is tagged into a family for review:

```text
raw_ema_price_level
ema_distance
volatility_atr
volatility_range_tr
candle_body_wick
momentum_return
oscillator
other
```

Risk flags:

```text
raw_price_level_stationarity_risk
absolute_volatility_regime_risk
boundary_missing_risk
```

Raw price-level EMA candidates are not rejected here, but they must be clearly marked as high stationarity risk.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/10_candidate_family_review_card_audit_only/
```

Output files:

```text
GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_AUDIT_ONLY_REPORT.md
gold_v3_10_summary.json
gold_v3_10_input_inventory.csv
gold_v3_10_candidate_family_review_rows.csv
gold_v3_10_feature_family_summary.csv
gold_v3_10_representative_review_rows.csv
gold_v3_10_boundary_card_rows.csv
gold_v3_10_decision_matrix.csv
gold_v3_10_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- Review cards only.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

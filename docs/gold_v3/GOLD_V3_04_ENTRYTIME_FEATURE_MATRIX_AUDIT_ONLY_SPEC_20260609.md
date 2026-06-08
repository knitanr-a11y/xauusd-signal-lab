# GOLD V3 04 entry-time feature matrix audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 03 completed label-only outcome evaluation. GOLD V3 04 creates an entry-time feature matrix using only information available at each entry time.

This step does not select candidates, optimize rules, train models, generate signals, call external APIs, or create ZIP output.

## Required upstream

```text
GOLD_V3_03_LABEL_OUTCOME_EVALUATION_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/03_label_outcome_evaluation_audit_only/gold_v3_03_summary.json
Files/FX_OUTPUTS/gold_v3/03_label_outcome_evaluation_audit_only/gold_v3_03_evaluated_label_rows.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_m15.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_h1.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_h4.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_d1.csv
```

## No-future rule

Feature rows are keyed by:

```text
feature_bar_open_utc
entry_time_utc
```

M15 features use the M15 bar that closes at entry time.

H1/H4/D1 features use native bars whose close time is less than or equal to entry time. H4 and D1 are not reconstructed from lower timeframes.

No outcome, profit, first touch, future high/low, timeout price, TP/SL result, or profile result column may be included in the feature matrix.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/04_entrytime_feature_matrix_audit_only/
```

Output files:

```text
GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_AUDIT_ONLY_REPORT.md
gold_v3_04_summary.json
gold_v3_04_input_inventory.csv
gold_v3_04_entry_feature_rows.csv
gold_v3_04_feature_column_inventory.csv
gold_v3_04_asof_join_audit.csv
gold_v3_04_base_entry_key_audit.csv
gold_v3_04_decision_matrix.csv
gold_v3_04_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- No outcome/profit columns in features.
- No candidate selection.
- No signals.
- No ZIP output.
- External actions remain OFF.

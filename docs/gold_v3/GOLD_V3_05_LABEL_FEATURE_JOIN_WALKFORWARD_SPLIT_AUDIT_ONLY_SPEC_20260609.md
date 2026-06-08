# GOLD V3 05 label-feature join and walk-forward split audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_SPLIT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 05 joins evaluated label rows from 03 with entry-time feature rows from 04, then fixes monthly walk-forward split boundaries before any candidate exploration.

This step does not select rules, optimize thresholds, train models, generate signals, call APIs, or create ZIP output.

## Required upstream

```text
GOLD_V3_03_LABEL_OUTCOME_EVALUATION_READY_AUDIT_ONLY
GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/03_label_outcome_evaluation_audit_only/gold_v3_03_summary.json
Files/FX_OUTPUTS/gold_v3/03_label_outcome_evaluation_audit_only/gold_v3_03_evaluated_label_rows.csv
Files/FX_OUTPUTS/gold_v3/04_entrytime_feature_matrix_audit_only/gold_v3_04_summary.json
Files/FX_OUTPUTS/gold_v3/04_entrytime_feature_matrix_audit_only/gold_v3_04_entry_feature_rows.csv
```

## Join keys

```text
feature_bar_open_utc
entry_time_utc
```

Every label row must join to exactly one entry-time feature row.

## Split policy

Use calendar-month walk-forward folds.

For each test month after at least two prior months exist:

```text
train = all months before validation month
validation = previous calendar month
test = current calendar month
```

Rows are not duplicated into fold datasets in this step. The script writes a fold matrix with counts and a base joined dataset with entry month.

## Leakage controls

Feature columns must not contain:

```text
outcome
profit
result
touch
tp
sl
timeout
future
label
horizon
```

Label/outcome columns may exist in the joined dataset, but they are explicitly separated from feature columns in the feature inventory.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/
```

Output files:

```text
GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_SPLIT_AUDIT_ONLY_REPORT.md
gold_v3_05_summary.json
gold_v3_05_input_inventory.csv
gold_v3_05_label_feature_join_rows.csv
gold_v3_05_feature_column_inventory.csv
gold_v3_05_month_row_counts.csv
gold_v3_05_walkforward_fold_matrix.csv
gold_v3_05_decision_matrix.csv
gold_v3_05_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- No candidate selection.
- No threshold optimization.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.

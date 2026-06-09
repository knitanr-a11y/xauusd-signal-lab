# GOLD V3 03 label outcome evaluation audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_03_LABEL_OUTCOME_EVALUATION_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 03 evaluates the label contract rows produced by GOLD V3 02B against native primary M5 candles.

This step is label/evaluation only. It does not create features, candidates, ranking rules, model training data, signals, live hooks, ZIP output, Discord notifications, MT5 orders, AI API calls, or final signal outputs.

## Required upstream

```text
GOLD_V3_02B_LABEL_GRID_CONTRACT_READY_WITH_SESSION_EXCLUSIONS_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/02b_label_grid_contract_audit_only/gold_v3_02b_summary.json
Files/FX_OUTPUTS/gold_v3/02b_label_grid_contract_audit_only/gold_v3_02b_entry_grid_contract_only.csv
Files/FX_OUTPUTS/gold_v3/01_candle_normalization_time_audit/canonical_candles/gold_v3_gold_hash_2025_primary_m5.csv
```

## Label evaluation contract

For each 02B contract row:

- Use `entry_time_utc` as the entry timestamp.
- Use `horizon_end_utc` as the evaluation horizon end.
- Use native primary M5 candles only.
- Find the M5 window from entry time inclusive to horizon end exclusive.
- If entry time is missing from M5, classify as `ENTRY_TIME_NOT_FOUND`.
- If no usable M5 window exists, classify as `NO_WINDOW`.
- If TP or SL is touched inside the M5 window, classify by the first touched M5 bar.
- If TP and SL are both touched on the same M5 bar, SL wins.
- If no TP/SL touch occurs before horizon end, classify as `TIMEOUT` and calculate timeout result from the last M5 close inside the window.

## Direction contract

For `LONG`:

```text
TP hit when M5 high >= tp_price
SL hit when M5 low <= sl_price
TIMEOUT result = timeout_close - entry_price
```

For non-`LONG` / short direction:

```text
TP hit when M5 low <= tp_price
SL hit when M5 high >= sl_price
TIMEOUT result = entry_price - timeout_close
```

## Output columns added

```text
label_evaluated
label_outcome
first_touch_time_utc
first_touch_bar_offset_m5
label_price_distance_result_usd
timeout_close_price
window_m5_bars
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/03_label_outcome_evaluation_audit_only/
```

Output files:

```text
GOLD_V3_03_LABEL_OUTCOME_EVALUATION_AUDIT_ONLY_REPORT.md
gold_v3_03_summary.json
gold_v3_03_input_inventory.csv
gold_v3_03_evaluated_label_rows.csv
gold_v3_03_profile_outcome_summary.csv
gold_v3_03_direction_outcome_summary.csv
gold_v3_03_decision_matrix.csv
gold_v3_03_blocker_matrix.csv
```

## Runtime path contract

The script must create the output directory with:

```python
p.mkdir(parents=True, exist_ok=True)
```

The script must still write the audit output files when inputs are missing, using blocked/input-review status.

## Decision matrix requirements

The decision matrix must verify:

```text
inputs_present
upstream_02b_ok
evaluated_rows_nonempty
all_rows_label_evaluated
features_created == False
signals_generated == False
zip_output_created == False
external_actions == False
```

## Blockers

Expected blockers:

```text
G3-03-001 02B inputs
G3-03-002 label evaluation
G3-03-003 feature/candidate/signal blocked by policy
G3-03-004 zip output disabled
G3-03-005 external actions off
```

## Safety

- GOLD V3 only.
- Future M5 candles are used only to assign labels.
- No live feature selector is produced here.
- No candidates are selected here.
- No ranking is performed here.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF.

## Downstream invalidation policy

Changing this spec text or adding a BAT does not invalidate stages 04-12.

Changing the Python label evaluation logic, output values, output columns, input files, TP/SL priority, timeout calculation, or status contract invalidates all downstream stages 04-12 and requires re-running 03 through 12.

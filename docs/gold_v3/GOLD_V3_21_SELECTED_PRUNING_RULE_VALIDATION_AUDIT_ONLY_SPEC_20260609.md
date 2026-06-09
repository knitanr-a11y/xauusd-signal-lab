# GOLD V3 21 selected pruning rule validation audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 21 validates selected Stage20 pruning scenarios, including the newly added July-rescue candidate:

```text
R1_ONLY_CD60_PRUNE_015
```

This stage is audit-only. It does not approve final candidates and does not enable live behavior.

## Required upstream

```text
GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/gold_v3_20_summary.json
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/gold_v3_20_scenario_metrics.csv
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/gold_v3_20_scenario_monthly_metrics.csv
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/gold_v3_20_loss_segment_audit.csv
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/gold_v3_20_month_bias_matrix.csv
```

## Selected candidates

Main PF uplift candidates:

```text
MAIN_R1_R2_CD90_PRUNE_133
MAIN_R1_R2_CD90_PRUNE_132
MAIN_R1_R2_CD120_PRUNE_122
```

Additional R1-only candidates:

```text
R1_ONLY_CD60_PRUNE_111
R1_ONLY_CD60_PRUNE_115
R1_ONLY_CD90_PRUNE_050
```

July-rescue candidate:

```text
R1_ONLY_CD60_PRUNE_015
```

## Validation checks

For each selected candidate, Stage 21 must show:

```text
all-period PF / win-rate / trades per day
July PF / win-rate / trades per day / result
worst month PF and result
negative months
drawdown and max loss streak
filter ids and filter descriptions
whether each filter is entry-pre-known
```

## Required outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/21_selected_pruning_rule_validation_audit_only/
```

Files:

```text
gold_v3_21_summary.json
gold_v3_21_input_inventory.csv
gold_v3_21_selected_candidate_validation.csv
gold_v3_21_selected_candidate_monthly_validation.csv
gold_v3_21_filter_traceability.csv
gold_v3_21_human_decision_template.csv
gold_v3_21_decision_matrix.csv
gold_v3_21_blocker_matrix.csv
GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_21_exception.txt
```

## Ready status

```text
GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_READY_AUDIT_ONLY
```

## Safety

- Audit-only.
- No daily cap.
- No final approval.
- No live enablement.
- No model training.
- No signal generation.
- No ZIP output.
- No external action.
- GOLD V2 / old GOLD / DISC8 remain quarantined.

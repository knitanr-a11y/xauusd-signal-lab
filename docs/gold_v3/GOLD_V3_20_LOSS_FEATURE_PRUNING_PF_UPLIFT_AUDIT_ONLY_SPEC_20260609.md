# GOLD V3 20 loss feature pruning PF uplift audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 20 audits the user's correction that PF / win-rate should be improved by pruning loss-prone entry-pre-known features, not by applying a daily trade cap.

This stage explicitly does not use daily caps.

The objective is:

```text
identify loss-prone entry conditions
remove only those conditions before entry
raise PF and win rate
preserve around 2 or more true trades/day where possible
find one additional candidate beyond MAIN_R1_R2 cooldown variants
keep rank 7/8 visible only as weak diagnostic/filter-rescue rows
```

This stage is audit-only. It does not approve final candidates and does not enable live behavior.

## Required upstream

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY
GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_summary.json
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_trade_ledger.csv
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_all_candidate_review.csv
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/gold_v3_18_summary.json
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/gold_v3_18_scenario_monthly_metrics.csv
Files/FX_OUTPUTS/gold_v3/19_final_audit_shortlist_human_decision_template_audit_only/gold_v3_19_summary.json
```

## Allowed pruning features

Only entry-pre-known fields may be used:

```text
source_rank
JST hour derived from entry_time_utc
JST weekday derived from entry_time_utc
h4_ret4
m15_atr28
h1_atr56
```

Not allowed:

```text
label_outcome
label_price_distance_result_usd
first_touch_time_utc
first_touch_bar_offset_m5
future month as a filter
daily trade cap
```

Outcome columns may be used only for audit scoring after a candidate filter is applied.

## Baseline

```text
MAIN_R1_R2
cooldown 60 minutes
no pruning
```

## Audit design

1. Build the baseline trade stream from Stage15 ledger.
2. Derive entry-pre-known fields such as JST hour and weekday.
3. Detect loss-enriched segments using baseline rows only.
4. Create candidate filters from those loss-prone segments.
5. Apply single filters and limited filter stacks.
6. Re-evaluate PF, win-rate, trades/day, drawdown, loss streak, and monthly stability.
7. Compare MAIN_R1_R2, R1_ONLY, R2_ONLY, and H1 diagnostic rows.

## Required outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/
```

Files:

```text
gold_v3_20_summary.json
gold_v3_20_input_inventory.csv
gold_v3_20_loss_segment_audit.csv
gold_v3_20_scenario_metrics.csv
gold_v3_20_scenario_monthly_metrics.csv
gold_v3_20_month_bias_matrix.csv
gold_v3_20_pf_uplift_recommendation.csv
gold_v3_20_decision_matrix.csv
gold_v3_20_blocker_matrix.csv
GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_20_exception.txt
```

ZIP output remains disabled.

## Ready status

```text
GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY
```

## Safety flags

These remain false:

```text
auto_approval
final_candidate_approval
threshold_finalization
model_training
signals_generated
zip_output_created
ai_api_called
discord_enabled
mt5_enabled
live_hook_enabled
live_evaluator_enabled
final_signal_enabled
gold_v2_live_sot_used
quarantined_legacy_artifacts_read
```

## Guardrails

- GOLD V3 only.
- No GOLD V2, old GOLD, DISC8, or quarantined legacy artifacts.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- Discord, MT5, AI API, live hook, live evaluator, and final signal remain OFF.

## BAT

```text
scripts/gold_v3_runtime/bat/GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_AUDIT_ONLY.bat
```

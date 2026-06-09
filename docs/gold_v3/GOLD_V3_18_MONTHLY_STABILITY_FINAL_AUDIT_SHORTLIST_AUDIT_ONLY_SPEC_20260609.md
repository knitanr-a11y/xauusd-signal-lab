# GOLD V3 18 monthly stability final audit shortlist audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 18 performs monthly stability review for the Stage 17 overlap/cooldown/spacing shortlist.

The objective is:

```text
select audit-only final-shortlist candidates
preserve at least 2 true trades/day where required
prefer high win rate and PF
check monthly stability and bad-month risk
keep rank 7/8 visible as weak diagnostic/drop-bias profiles, not silently discarded
```

This stage does not approve final candidates and does not enable live behavior.

## Required upstream

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_READY_AUDIT_ONLY
GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_summary.json
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_trade_ledger.csv
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_summary.json
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_all_candidate_review.csv
Files/FX_OUTPUTS/gold_v3/17_overlap_cooldown_spacing_audit_only/gold_v3_17_summary.json
Files/FX_OUTPUTS/gold_v3/17_overlap_cooldown_spacing_audit_only/gold_v3_17_portfolio_spacing_metrics.csv
Files/FX_OUTPUTS/gold_v3/17_overlap_cooldown_spacing_audit_only/gold_v3_17_candidate_cooldown_metrics.csv
Files/FX_OUTPUTS/gold_v3/17_overlap_cooldown_spacing_audit_only/gold_v3_17_spacing_recommendation.csv
```

## Shortlist scenarios

Primary:

```text
PRIMARY_MAIN_BALANCED: MAIN_R1_R2 cooldown 60
PRIMARY_MAIN_CONSERVATIVE: MAIN_R1_R2 cooldown 120
PRIMARY_MAIN_AGGRESSIVE: MAIN_R1_R2 cooldown 30
```

Auxiliary:

```text
AUX_H1_BEST_R3: MAIN_R1_R2_PLUS_H1_BEST_R3 cooldown 120
AUX_H1_R4: MAIN_R1_R2_PLUS_H1_R4 cooldown 120
AUX_H1_R6: MAIN_R1_R2_PLUS_H1_R6 cooldown 120
```

Diagnostics:

```text
DIAG_H1_ONLY_R3 cooldown 120
DIAG_H1_ONLY_R4 cooldown 120
DIAG_H1_ONLY_R6 cooldown 120
WEAK_DIAG_H1_ONLY_R7 cooldown 120
WEAK_DIAG_H1_ONLY_R8 cooldown 120
```

Rank 7 and rank 8 must remain visible in output as weak diagnostic/drop-bias profiles.

## Outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/
```

Required output files:

```text
gold_v3_18_summary.json
gold_v3_18_input_inventory.csv
gold_v3_18_scenario_monthly_metrics.csv
gold_v3_18_scenario_stability_summary.csv
gold_v3_18_rank_retention_review.csv
gold_v3_18_shortlist_recommendation.csv
gold_v3_18_decision_matrix.csv
gold_v3_18_blocker_matrix.csv
GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_18_exception.txt
```

ZIP output remains disabled.

## Ready status

```text
GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY
```

## Safety

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
scripts/gold_v3_runtime/bat/GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_AUDIT_ONLY.bat
```

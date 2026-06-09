# GOLD V3 17 overlap cooldown spacing audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 17 audits overlap, duplicate timestamps, cooldown, and spacing after Stage 16 all-candidate review.

The audit keeps all Stage 16 reviewed rows in scope, including weak/deferred h1_atr56 profiles rank 7 and rank 8.

The objective is:

```text
keep at least 2 true trades/day
reduce overlap and over-frequency
reduce drawdown / loss streak risk
compare h1_atr56 TP/SL profiles without treating them as independent entry ideas
preserve high PF and win-rate candidates
```

This stage is audit-only. It is not final candidate approval and not live approval.

## Required upstream

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_summary.json
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_trade_ledger.csv
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_candidate_metrics.csv
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_summary.json
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_all_candidate_review.csv
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_h1_atr56_profile_comparison.csv
```

## Inclusion rule

All Stage 16 reviewed ranks must be included:

```text
1, 2, 3, 4, 6, 7, 8
```

Rank 7 and rank 8 are included as weak h1_atr56 comparison profiles, not silently dropped.

## Cooldown grid

```text
0, 15, 30, 60, 120, 240, 480, 720, 1440 minutes
```

The grid is an audit grid only. It does not finalize live cooldown.

## Candidate-level audit

For each candidate rank, Stage 17 applies local cooldown and writes metrics for every cooldown value.

## Portfolio-level audit

Stage 17 also audits priority-deduplicated portfolio scenarios:

```text
MAIN_R1_R2
MAIN_R1_R2_PLUS_H1_BEST_R3
MAIN_R1_R2_PLUS_H1_R4
MAIN_R1_R2_PLUS_H1_R6
H1_ONLY_R3
H1_ONLY_R4
H1_ONLY_R6
H1_ONLY_R7
H1_ONLY_R8
ALL_7_DIAGNOSTIC_PRIORITY_DEDUP
```

Same-timestamp duplicates are priority-deduplicated before cooldown in portfolio scenarios.

The all-7 scenario is diagnostic only and not a live portfolio recommendation.

## Metrics

```text
rows_before_spacing
rows_after_spacing
unique_entry_times_after_spacing
trades_per_calendar_day
trades_per_active_day
win_rate_result_positive
profit_factor
sum_result_usd
avg_result_usd
median_result_usd
gross_profit_usd
gross_loss_abs_usd
max_drawdown_usd
max_consecutive_losses
tp_count
sl_count
timeout_count
objective_2_trades_per_day_pass
score_spacing_objective
```

## Outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/17_overlap_cooldown_spacing_audit_only/
```

Required output files:

```text
gold_v3_17_summary.json
gold_v3_17_input_inventory.csv
gold_v3_17_candidate_cooldown_metrics.csv
gold_v3_17_portfolio_spacing_metrics.csv
gold_v3_17_overlap_diagnostics.csv
gold_v3_17_spacing_recommendation.csv
gold_v3_17_decision_matrix.csv
gold_v3_17_blocker_matrix.csv
GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_17_exception.txt
```

ZIP output remains disabled.

## Ready status

```text
GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_READY_AUDIT_ONLY
```

## Blocked status

```text
GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_BLOCKED_AUDIT_ONLY
```

## Safety flags

These must remain false:

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
scripts/gold_v3_runtime/bat/GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_AUDIT_ONLY.bat
```

Because the BAT is under `scripts/gold_v3_runtime/bat/`, it must return to repo root with:

```bat
cd /d "%~dp0\..\..\.."
```

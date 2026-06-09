# GOLD V3 22 within-candidate loss feature pruning audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 22 corrects the Stage21 next-step direction.

The goal is not to switch between seasonal candidates. The goal is to take each selected Stage21 candidate and further remove loss-prone entry-pre-known feature areas that remain inside that candidate.

This stage is audit-only. It does not approve final candidates and does not enable live behavior.

## Required upstream

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY
GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_summary.json
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_trade_ledger.csv
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/gold_v3_16_all_candidate_review.csv
Files/FX_OUTPUTS/gold_v3/20_loss_feature_pruning_pf_uplift_audit_only/gold_v3_20_summary.json
Files/FX_OUTPUTS/gold_v3/21_selected_pruning_rule_validation_audit_only/gold_v3_21_summary.json
Files/FX_OUTPUTS/gold_v3/21_selected_pruning_rule_validation_audit_only/gold_v3_21_selected_candidate_validation.csv
Files/FX_OUTPUTS/gold_v3/21_selected_pruning_rule_validation_audit_only/gold_v3_21_filter_traceability.csv
```

## Selected candidates

Stage22 starts from the Stage21 selected candidates, including:

```text
MAIN_R1_R2_CD90_PRUNE_133
MAIN_R1_R2_CD90_PRUNE_132
MAIN_R1_R2_CD120_PRUNE_122
R1_ONLY_CD60_PRUNE_111
R1_ONLY_CD60_PRUNE_115
R1_ONLY_CD90_PRUNE_050
R1_ONLY_CD60_PRUNE_015
```

## What is allowed

Only entry-pre-known feature pruning is allowed:

```text
source_rank
JST hour derived from entry_time_utc
JST weekday derived from entry_time_utc
h4_ret4
m15_atr28
h1_atr56
```

Stage22 may use outcomes only to identify and score loss-prone segments during audit. The final filter description must still be based on entry-pre-known features only.

## What is not allowed

```text
seasonal switching
month as a live filter
daily cap
future outcome as a live filter
model training
threshold finalization
signal generation
live enablement
```

## Audit design

For each selected candidate:

1. Reconstruct its existing Stage21 filter stack.
2. Recreate its trade stream from Stage15 ledger.
3. Identify remaining loss-prone feature segments within that candidate.
4. Test one or two additional entry-pre-known filters.
5. Compare before vs after:
   - PF
   - win-rate
   - trades/day
   - July PF/result
   - worst month
   - negative months
   - drawdown
   - max loss streak
6. Produce recommended further-pruned variants.

## Required outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/
```

Files:

```text
gold_v3_22_summary.json
gold_v3_22_input_inventory.csv
gold_v3_22_base_candidate_metrics.csv
gold_v3_22_remaining_loss_segment_audit.csv
gold_v3_22_further_pruned_candidate_metrics.csv
gold_v3_22_further_pruned_monthly_metrics.csv
gold_v3_22_filter_traceability.csv
gold_v3_22_recommendation.csv
gold_v3_22_decision_matrix.csv
gold_v3_22_blocker_matrix.csv
GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_22_exception.txt
```

## Ready status

```text
GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY
```

## Safety

- Audit-only.
- No switching logic.
- No month filter.
- No daily cap.
- No final approval.
- No live enablement.
- No model training.
- No signal generation.
- No ZIP output.
- No external action.
- GOLD V2 / old GOLD / DISC8 remain quarantined.

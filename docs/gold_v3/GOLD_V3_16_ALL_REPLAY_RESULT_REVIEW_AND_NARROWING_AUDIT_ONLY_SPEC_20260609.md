# GOLD V3 16 all replay result review and narrowing audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 16 reviews all GOLD V3 Stage 15 audit-only replay candidates, including candidates previously described as defer/narrowing profiles.

The user objective is:

```text
at least 2 true trades/day
keep win rate and PF high
keep multiple candidates for comparison
include deferred h1_atr56 TP/SL profiles in the audit
```

This stage is not final selection. It produces an audit-only narrowing recommendation.

## Required upstream

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
```

Required Stage 15 inputs:

```text
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_summary.json
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_candidate_metrics.csv
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_family_metrics.csv
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_monthly_metrics.csv
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/gold_v3_15_replay_overlap_audit.csv
```

## Inclusion rule

All seven Stage 15 replay candidate metric rows must be reviewed.

The h1_atr56 rows are not independent entry ideas, but they must still be audited as TP/SL/horizon profile comparisons:

```text
rank 3: USDPRICE_TP100_SL40_H96
rank 4: USDPRICE_TP80_SL30_H64
rank 6: USDPRICE_TP50_SL20_H48
rank 7: USDPRICE_TP30_SL10_H32
rank 8: USDPRICE_TP20_SL10_H28
```

No previously deferred profile may be silently dropped in Stage 16.

## Review dimensions

For every candidate:

```text
true trades/day
win rate from positive label result
profit factor
max drawdown
max consecutive losses
sum result
average result
TP rate
timeout count
positive months
negative months
negative month rate
minimum monthly result
median monthly PF
minimum monthly PF
median monthly win rate
objective-fit score
recommendation bucket
```

## Recommendation buckets

```text
KEEP_MAIN
KEEP_MAIN_WITH_MONTHLY_FILTER_REVIEW
KEEP_AUXILIARY_FAMILY_BEST
KEEP_FOR_H1_FAMILY_PROFILE_COMPARISON
AUDITED_BUT_NARROW_OR_DROP
REQUEST_MORE_NARROWING_AUDIT
DO_NOT_KEEP_FOR_2_TRADES_PER_DAY_OBJECTIVE
```

These are audit-only recommendations, not approvals.

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/16_all_replay_result_review_and_narrowing_audit_only/
```

## Required outputs

```text
gold_v3_16_summary.json
gold_v3_16_input_inventory.csv
gold_v3_16_all_candidate_review.csv
gold_v3_16_monthly_robustness_review.csv
gold_v3_16_h1_atr56_profile_comparison.csv
gold_v3_16_narrowing_recommendation.csv
gold_v3_16_decision_matrix.csv
gold_v3_16_blocker_matrix.csv
GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_16_exception.txt
```

ZIP output is disabled.

## Status values

Ready:

```text
GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_READY_AUDIT_ONLY
```

Blocked:

```text
GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_BLOCKED_AUDIT_ONLY
```

Exception:

```text
GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_EXCEPTION_AUDIT_ONLY
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
scripts/gold_v3_runtime/bat/GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_AUDIT_ONLY.bat
```

Because the BAT is under `scripts/gold_v3_runtime/bat/`, it must return to repo root with:

```bat
cd /d "%~dp0\..\..\.."
```

It runs only:

```bat
python scripts\gold_v3_runtime\gold_v3_16_all_replay_result_review_and_narrowing_audit_only.py --repo-root "%REPO_ROOT%"
```

or the same with `py -3`.

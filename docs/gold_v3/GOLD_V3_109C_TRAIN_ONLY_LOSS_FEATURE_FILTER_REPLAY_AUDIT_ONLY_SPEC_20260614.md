# GOLD V3 Stage109C Spec — TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY
```

## Why this stage exists

Stage109B found post-hoc loss-heavy entry-time feature patterns and candidate filters:

```text
status: GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_READY_AUDIT_ONLY
decision: LOSS_FEATURE_FINGERPRINT_READY_FOR_109C_TRAIN_ONLY_REPLAY
ledger_rows: 5571
candidate_filter_rows: 127
```

Top post-hoc examples included:

```text
entry_hour <= 5
m15_rsi14 <= 40.5041
m15_dist_atr >= -0.0219
entry_hour <= 3
h4_atr28 >= 46.2521
m15_dist_atr >= 0.1542
m15_rsi14 <= 37.7016
```

These are promising diagnostics, but they are not approved filters because they were selected post-hoc.

## Purpose

Stage109C validates the loss-feature idea with train-only/walk-forward replay.

It must:

1. Read the Stage109 selected base ledger.
2. Read Stage109B candidate feature diagnostics only as the feature/op search universe.
3. For each train/target split, select filter thresholds using only train rows.
4. Apply the selected filter to the target rows.
5. Compare target retained results against target base results.
6. Decide whether the loss-feature filter family survives forward validation.

## Strict anti-leakage rule

The target window outcome must never be used to select the filter for that target window.

Allowed train-only inputs for filter selection:

```text
train entry-time features
train result_usd labels
```

Forbidden:

```text
target result_usd during filter selection
target exit_dt during filter selection
post-hoc thresholds from full sample as final thresholds
```

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_candidate_filter_diagnostics.csv
```

## Default validation

Use active-trade-day walk-forward splits:

```text
lookback_active_days: 20, 50
target_active_days: 5, 10
```

For each split:

1. train = previous lookback active days
2. target = next target active days
3. candidate thresholds are generated from train quantiles only
4. best train filter is selected by train retained WR/PF/retention score
5. selected filter is applied to target

## Outputs

```text
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_walkforward_filter_summary.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_walkforward_target_ledger.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_best_combo_summary.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_feature_family_survival.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_blocker_matrix.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_validation_matrix.csv
FX_OUTPUTS/gold_v3/109cc/gold_v3_109c_summary.json
FX_OUTPUTS/gold_v3/109cc/GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/109cc/paste_me.txt
```

## Gates

Primary gate:

```text
walkforward WR >= base WR + 0.5 percentage point
walkforward PF >= base PF
retention >= 70%
sum_result_usd >= base sum_result_usd
negative_month_count <= base negative_month_count
```

Review gate:

```text
walkforward WR >= base WR
walkforward PF >= base PF
retention >= 65%
sum_result_usd drawdown no worse than -1.0% of base sum_result_usd
```

## Decisions

Allowed decisions:

```text
TRAIN_ONLY_LOSS_FEATURE_FILTER_PRIMARY_READY_FOR_REVIEW
TRAIN_ONLY_LOSS_FEATURE_FILTER_REVIEW_READY_NEEDS_HUMAN_DECISION
TRAIN_ONLY_LOSS_FEATURE_FILTER_NOT_CONFIRMED_KEEP_109_BASE
TRAIN_ONLY_LOSS_FEATURE_FILTER_BLOCKED_INPUT_INCOMPLETE
```

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.

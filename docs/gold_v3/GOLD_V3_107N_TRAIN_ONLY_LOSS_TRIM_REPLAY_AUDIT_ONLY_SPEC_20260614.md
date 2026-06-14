# GOLD V3 Stage107N Spec — TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY
```

## Why this stage exists

Stage107M found a strong post-hoc diagnostic trim:

```text
best_filter: ALL m15_dist_atr >= 0.1153788860705594
base WR: 60.27%
retained WR: 63.43%
base PF: 2.55
retained PF: 2.93
retention: 79.92%
min_regime_wr: 63.25%
```

But Stage107M explicitly marked this as:

```text
posthoc_filters_not_final=true
final_rule_approval=false
```

Therefore Stage107N must test whether loss-trim rules could have been selected using only past information before each target month.

## Purpose

Stage107N performs monthly train-only / walk-forward replay for loss-trim filters.

For each target month:

1. Use only rows with `entry_dt < target_month_start` as training history.
2. Enumerate entry-known filter candidates on the training history only.
3. Rank filters using training history only.
4. Apply the selected filters to the target month.
5. Aggregate performance across all target months.

## Important live-known limitation

The current 107L/107M ledger still lacks `exit_dt`.

Because of that, Stage107N is **train-split proxy**, not resolved-only live faithful.

It may confirm that a filter can be selected before a target month using prior rows, but it must not claim strict live readiness until a resolved ledger can prove that each historical label was known before selection.

Strict resolved-only requirement remains:

```text
exit_dt <= current entry_dt
```

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_train_only_loss_trim_candidates.csv
```

The 107M files are used only as diagnostics and seeds. The replay must still select filters from train history only.

## Entry-known filter columns

Permitted examples:

```text
side
m15_atr28 / m15_rsi14 / m15_up / m15_close_gt_ema20 / m15_dist_atr / m15_range_atr
h1_atr28 / h1_rsi14 / h1_up / h1_close_gt_ema20 / h1_dist_atr / h1_range_atr
h4_atr28 / h4_rsi14 / h4_up / h4_close_gt_ema20 / h4_dist_atr / h4_range_atr
d1_atr28 / d1_rsi14 / d1_up / d1_close_gt_ema20 / d1_dist_atr / d1_range_atr
feature_score / ledger_score / score
```

Forbidden as filter inputs:

- future TP/SL result
- future exit result
- future high/low/close
- unresolved horizon result
- open/in-progress candles
- target-month result when selecting that target-month filter

## Outputs

```text
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_monthly_walkforward_selected_filters.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_walkforward_trade_ledger.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_walkforward_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_walkforward_regime_metrics.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_seed_filter_replay_metrics.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_validation_matrix.csv
FX_OUTPUTS/gold_v3/107nc/gold_v3_107n_summary.json
FX_OUTPUTS/gold_v3/107nc/GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107nc/paste_me.txt
```

## Gates

Primary train-only replay gate:

```text
walkforward WR >= 62.5%
walkforward PF >= 2.70
retention >= 65%
min_regime_wr >= 60%
negative_month_count == 0
```

Review gate:

```text
walkforward WR improves vs base by >= 1.0 percentage point
walkforward PF improves vs base
retention >= 65%
min_regime_wr >= 59%
```

## Decisions

Allowed decisions:

```text
TRAIN_ONLY_LOSS_TRIM_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY
TRAIN_ONLY_LOSS_TRIM_REVIEW_READY_FOR_DEEPER_REPLAY
TRAIN_ONLY_LOSS_TRIM_NOT_CONFIRMED_NEED_ALTERNATIVE_FILTERS
TRAIN_ONLY_LOSS_TRIM_BLOCKED_INPUT_INCOMPLETE
```

Even if primary passes, live_ready must remain false because `exit_dt` is still required for strict resolved-only replay.

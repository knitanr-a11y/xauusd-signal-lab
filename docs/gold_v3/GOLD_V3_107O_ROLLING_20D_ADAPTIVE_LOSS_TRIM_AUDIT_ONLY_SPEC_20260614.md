# GOLD V3 Stage107O Spec — ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY
```

## Why this stage exists

Stage107N tested monthly train-only loss trim. It improved PF modestly, but did not confirm the monthly approach:

```text
base WR: 60.27%
walkforward WR: 60.66%
base PF: 2.55
walkforward PF: 2.64
walkforward retention: 87.23%
min_regime_wr: 59.64%
negative_month_count: 1
primary_gate: false
review_gate: false
```

The user correctly pointed out that month-based adaptation is too coarse. Market regimes shift inside calendar months. A rolling recent-history window such as past 20 active trade days should adapt faster than monthly windows.

## Purpose

Stage107O performs a rolling adaptive loss-trim audit:

1. Use the 107L rehydrated best-policy ledger.
2. Walk forward by small target active-day windows.
3. For each target window, select filters using only the prior rolling lookback window.
4. Apply the selected filter to the target window.
5. Aggregate performance by total, regime, month, and rolling window.

Default design:

```text
lookback_active_days: 20
target_active_days: 5
min_train_rows: 300
min_removed: 15
min_retention: 65%
```

## Important limitation

The current ledger still lacks `exit_dt`.

Therefore Stage107O is still a train-split proxy and cannot claim strict live readiness.

Strict live/replay requirement remains:

```text
exit_dt <= current entry_dt
```

## Progress logging requirement

Stage107O must print progress in the terminal during execution:

```text
progress   0.0% complete / 100.0% remaining | step 0/N | start
progress  25.0% complete /  75.0% remaining | step X/N | window=...
progress 100.0% complete /   0.0% remaining | step N/N | DONE
```

This is separate from importing Python modules at the top of the file. Imports only reduce runtime setup ambiguity; explicit `prog()` logging is required to show progress.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
```

Optional comparison source:

```text
FX_OUTPUTS/gold_v3/107nc/paste_me.txt
```

## Entry-known filter columns

Allowed examples:

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
- target-window result when selecting the filter for that window

## Outputs

```text
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_rolling_window_selected_filters.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_rolling_trade_ledger.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_rolling_window_metrics.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_rolling_regime_metrics.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_rolling_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_validation_matrix.csv
FX_OUTPUTS/gold_v3/107oc/gold_v3_107o_summary.json
FX_OUTPUTS/gold_v3/107oc/GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107oc/paste_me.txt
```

## Gates

Primary rolling proxy gate:

```text
rolling WR >= 62.5%
rolling PF >= 2.70
retention >= 65%
min_regime_wr >= 60%
negative_month_count == 0
```

Review gate:

```text
rolling WR gain vs comparable base >= 1.0 percentage point
rolling PF improves vs comparable base
retention >= 65%
min_regime_wr >= 59.5%
```

## Allowed decisions

```text
ROLLING_20D_ADAPTIVE_LOSS_TRIM_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY
ROLLING_20D_ADAPTIVE_LOSS_TRIM_REVIEW_READY_FOR_PARAMETER_SWEEP
ROLLING_20D_ADAPTIVE_LOSS_TRIM_NOT_CONFIRMED_NEED_PARAMETER_SWEEP
ROLLING_20D_ADAPTIVE_LOSS_TRIM_BLOCKED_INPUT_INCOMPLETE
```

Even if the rolling proxy passes, `live_ready` remains false until a resolved `exit_dt` ledger supports strict replay.

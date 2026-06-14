# GOLD V3 Stage107M Spec — PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY
```

## Why this stage exists

Stage107K2 / 107L found a promising balanced-60 policy:

```text
best_policy_key: density_safe||100||Q0.6
best_min_wr: 0.601742696053306
best_min_pf: 2.5352617898638443
best_sum_trades: 8565
rehydration_metric_parity_pass: true
```

The main performance problem is not 2026 high-vol. The first problem side is `REGIME_2026_Q1Q2`, especially `2026-03`:

```text
2026-03 trades: 188
2026-03 WR: 36.70%
2026-03 PF: 1.2469
2026-03 unique_trade_days: 3
2026-03 max_day_trade_share: 71.28%
```

Secondary weak areas:

```text
2025-10 WR: 52.76%
2025-07 WR: 54.34%
2026-04 WR: 55.08%
2025-11 WR: 57.66%
```

Stage107M prioritizes problem-regime loss trimming before attempting another health-gate stage. Health gate remains blocked until `exit_dt` exists.

## Purpose

Use the 107L rehydrated best-policy ledger to find audit-only loss-trim candidates for weak regimes/months.

This stage must:

1. Identify problem months from 107L monthly diagnostics.
2. Enumerate only entry-known filters from the 107L rehydrated ledger.
3. Prefer filters that reduce low-quality buckets while preserving multi-regime performance.
4. Separate post-hoc diagnostic ranking from train-only validation.
5. Keep live_ready=false.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_best_policy_monthly_diagnostics.csv
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
```

## Entry-known feature set

The script may inspect only columns already present at entry time, for example:

```text
side
m15_atr28 / m15_rsi14 / m15_up / m15_close_gt_ema20 / m15_dist_atr / m15_range_atr
h1_atr28 / h1_rsi14 / h1_up / h1_close_gt_ema20 / h1_dist_atr / h1_range_atr
h4_atr28 / h4_rsi14 / h4_up / h4_close_gt_ema20 / h4_dist_atr / h4_range_atr
d1_atr28 / d1_rsi14 / d1_up / d1_close_gt_ema20 / d1_dist_atr / d1_range_atr
feature_score / ledger_score / score
```

It must not use future TP/SL, future exit result, future OHLC, unresolved horizon, or open candles as filter inputs.

## Important leakage rule

This stage is allowed to use final `result_usd` only as a label for offline audit.

Any filter discovered from the full 107L ledger is **diagnostic-only** and cannot become a live rule unless a later train-only/walk-forward replay confirms that the rule would have existed before the evaluated entries.

## Health gate status

Stage107L confirmed:

```text
missing_exit_dt_for_resolved_only_health_gate
```

Therefore Stage107M must not simulate rolling health gates unless `exit_dt` is present and complete. The expected behavior is to keep health gate blocked and focus on loss-trim diagnostics.

## Required outputs

```text
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_problem_months.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_problem_side_diagnostics.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_train_only_loss_trim_candidates.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_best_filter_regime_metrics.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_best_filter_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_validation_matrix.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_summary.json
FX_OUTPUTS/gold_v3/107mc/GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107mc/paste_me.txt
```

## Success criteria

Stage107M may be READY when:

- Required 107L files exist.
- Problem months are identified.
- At least one loss-trim frontier row is produced.
- All outputs are audit-only.
- live_ready=false.
- No source CSV, candidate pool, runtime, live hook, final signal, Discord, MT5, or AI API is changed.

## What Stage107M may not claim

Stage107M must not claim:

- final candidate approval
- live readiness
- health-gate success
- Discord/MT5 readiness
- that a post-hoc filter is safe for live use

## Next stage after 107M

If a promising filter exists, next stage should be:

```text
107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY
```

That next stage must verify live-reproducibility by selecting filters only from prior resolved history, then evaluating later data.

# GOLD V3 Stage107P Spec — ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY
```

## Why this stage exists

Stage107O tested one rolling setting:

```text
lookback_active_days: 20
target_active_days: 5
```

It did not confirm the rolling trim:

```text
base_eval WR: 60.34%
rolling WR: 59.35%
base_eval PF: 2.624
rolling PF: 2.586
rolling_retention: 61.99%
min_regime_wr: 57.30%
primary_gate: false
review_gate: false
```

The user proposed testing shorter adaptive windows if 20 active days remains too slow or unstable:

```text
lookback_active_days: 10
lookback_active_days: 5
```

## Purpose

Stage107P runs a rolling parameter sweep for adaptive loss trim.

Default sweep:

```text
lookback_active_days: 20,10,5
target_active_days: 5,3,1
```

For each combination:

1. Use only the prior rolling active-day lookback window as training history.
2. Select an entry-known loss-trim filter from that training window only.
3. Apply it to the next target active-day window.
4. Aggregate comparable base-vs-rolling metrics.
5. Rank combinations by walk-forward quality.

## Progress logging requirement

Stage107P must show explicit progress percentage during execution:

```text
progress   0.0% complete / 100.0% remaining | step 0/N | start
progress  50.0% complete /  50.0% remaining | step X/N | combo=...
progress 100.0% complete /   0.0% remaining | step N/N | DONE
```

## Current limitation

The 107L best-policy ledger lacks `exit_dt`, so this stage remains a rolling train-split proxy.

It must not claim strict live readiness until a resolved ledger proves:

```text
exit_dt <= current entry_dt
```

## Required input

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_parameter_sweep_summary.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_all_selected_filters.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_all_window_metrics.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_best_combo_trade_ledger.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_best_combo_regime_metrics.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_best_combo_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_validation_matrix.csv
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_summary.json
FX_OUTPUTS/gold_v3/107pc/GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107pc/paste_me.txt
```

## Gates

Primary gate per best combination:

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
ROLLING_LOOKBACK_SWEEP_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY
ROLLING_LOOKBACK_SWEEP_REVIEW_READY_FOR_FILTER_STABILITY_AUDIT
ROLLING_LOOKBACK_SWEEP_NOT_CONFIRMED_NEED_RULE_FAMILY_CHANGE
ROLLING_LOOKBACK_SWEEP_BLOCKED_INPUT_INCOMPLETE
```

Even if the proxy passes, live_ready remains false.

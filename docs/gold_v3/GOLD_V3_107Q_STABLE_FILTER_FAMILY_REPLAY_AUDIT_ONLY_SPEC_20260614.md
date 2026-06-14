# GOLD V3 Stage107Q Spec — STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY
```

## Why this stage exists

Stages 107O/107P tested adaptive rolling loss-trim filters. Shortening lookback from 20 to 10/5 active days did not solve the problem.

107P best combination:

```text
best_combo_key: L5_T5
base WR: 60.08%
rolling WR: 59.52%
base PF: 2.569
rolling PF: 2.480
retention: 66.07%
min_regime_wr: 58.78%
primary_gate: false
review_gate: false
```

This implies the failure is not merely lookback length. The free rolling feature-selection method is unstable: it often removes strong trades in the target window.

Stage107Q changes the rule family. Instead of reselecting any feature every window, it audits **stable filter families**.

## Purpose

Stage107Q asks:

> Do any fixed filter families, especially the 107M-identified `m15_dist_atr` family, remain useful when only thresholds are selected from prior history?

This stage must separate:

1. diagnostic seed families from 107M posthoc results
2. train-only threshold selection inside each family
3. strict resolved-only replay, which remains blocked until `exit_dt` exists

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107pc/gold_v3_107p_parameter_sweep_summary.csv
```

## Method

Stage107Q builds stable families from the top unique 107M frontier rows:

```text
family = feature + op + side_scope
```

For each family:

1. Use rolling active-day windows.
2. In each train window, select only a threshold for that family.
3. Apply the threshold to the target window.
4. Aggregate total / regime / month metrics.
5. Rank families by WR/PF gain, retention, min_regime_wr, and stability.

Default parameters:

```text
family_top_n: 30
lookback_active_days: 20,10,5
target_active_days: 5,3,1
min_train_rows: 150
min_removed: 10
min_retention: 65%
```

## Important leakage rule

107M seed families are diagnostic. A family discovered posthoc is not final simply because it ranks well here.

A later stage must validate final candidates using a clean train-only family-selection stage or resolved-only history.

## Current limitation

The 107L ledger lacks `exit_dt`.

Therefore Stage107Q is a proxy audit only. It must not claim strict live readiness until a resolved ledger proves:

```text
exit_dt <= current entry_dt
```

## Progress logging requirement

Stage107Q must show progress:

```text
progress   0.0% complete / 100.0% remaining | step 0/N | start
progress  50.0% complete /  50.0% remaining | step X/N | family=... combo=...
progress 100.0% complete /   0.0% remaining | step N/N | DONE
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_family_sweep_summary.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_all_selected_thresholds.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_all_window_metrics.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_regime_metrics.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_validation_matrix.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_summary.json
FX_OUTPUTS/gold_v3/107qc/GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107qc/paste_me.txt
```

## Gates

Primary proxy gate:

```text
family WR >= 62.5%
family PF >= 2.70
retention >= 65%
min_regime_wr >= 60%
negative_month_count == 0
```

Review gate:

```text
family WR gain vs comparable base >= 1.0 percentage point
family PF improves vs comparable base
retention >= 65%
min_regime_wr >= 59.5%
```

## Allowed decisions

```text
STABLE_FILTER_FAMILY_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY
STABLE_FILTER_FAMILY_REVIEW_READY_FOR_CLEAN_FAMILY_SELECTION_REPLAY
STABLE_FILTER_FAMILY_NOT_CONFIRMED_NEED_NON_FILTER_RULE_CHANGE
STABLE_FILTER_FAMILY_BLOCKED_INPUT_INCOMPLETE
```

Even if primary passes, `live_ready` remains false.

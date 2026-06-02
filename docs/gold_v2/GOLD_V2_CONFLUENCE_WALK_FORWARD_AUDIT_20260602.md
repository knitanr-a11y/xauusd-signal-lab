# GOLD V2 confluence walk-forward audit

Created: 2026-06-02
Status: AUDIT RESULT SNAPSHOT

## 1. Purpose

This document records the first GOLD V2 confluence walk-forward audit after saving the origin/confluence current state.

This is not a live/demo runtime approval document.

## 2. Input

The audit used the current confluence cluster outputs generated from the GOLD V2 origin/filter portfolio:

```text
gold_v2_confluence_score_outputs/gold_v2_confluence_cluster_ledger.csv
gold_v2_confluence_score_outputs/gold_v2_confluence_cluster_members.csv
```

## 3. Method

This run is a **policy-level walk-forward**.

It does not re-mine all raw candidate conditions per fold. Instead, it uses the fixed current V2 candidate/filter/confluence universe and tests whether confluence policies chosen from earlier months continue to work in the next month.

Months:

```text
2025-12, 2026-01, 2026-02, 2026-03, 2026-04, 2026-05, 2026-06
```

Minimum train window:

```text
3 months
```

Folds:

```text
Fold 1: train 2025-12..2026-02 -> test 2026-03
Fold 2: train 2025-12..2026-03 -> test 2026-04
Fold 3: train 2025-12..2026-04 -> test 2026-05
Fold 4: train 2025-12..2026-05 -> test 2026-06
```

Selection criteria for a policy on train months:

```text
train_count >= 20
train_win_rate >= 0.60
train_pf >= 1.50
train_total_r > 0
train_max_loss_streak <= 5
train_avg_monthly_count <= 80
```

Top-N selected per fold:

```text
10 policies by train composite score
```

## 4. Important limitation

This is not full no-leak re-mining.

The candidate/filter universe is already mined from previous steps. Therefore this audit should be interpreted as:

```text
Can train-selected confluence policies generalize to later months inside the current mined candidate universe?
```

not as:

```text
Can a completely fresh mining process discover the same rules without any future information?
```

A stricter future audit must rebuild candidate/filter/confluence selection using only earlier months.

## 5. Top-1-by-fold result

For each fold, the top train-selected policy was tested on the next month.

```text
Fold 1 test 2026-03:
  scenario: DIVERSIFIED_TOP2_PER_ORIGIN
  policy: stacked_score_sum_ge_20
  count: 55
  win_rate: 69.09%
  PF: 3.78
  total_r: +146.0
  max_loss_streak: 3

Fold 2 test 2026-04:
  scenario: DIVERSIFIED_TOP2_PER_ORIGIN
  policy: stacked_no_conflict_min_same_count_2
  count: 76
  win_rate: 73.68%
  PF: 3.96
  total_r: +145.0
  max_loss_streak: 2

Fold 3 test 2026-05:
  scenario: DIVERSIFIED_TOP2_PER_ORIGIN
  policy: stacked_score_sum_ge_20
  count: 38
  win_rate: 76.32%
  PF: 6.22
  total_r: +130.5
  max_loss_streak: 2

Fold 4 test 2026-06:
  scenario: DIVERSIFIED_TOP2_PER_ORIGIN
  policy: stacked_no_conflict_min_same_count_2
  count: 3
  win_rate: 66.67%
  PF: 0.94
  total_r: -0.5
  max_loss_streak: 1
```

Combined top-1-by-fold evidence:

```text
count: 172
win_rate: 72.67%
PF: 4.11
total_r: +421.0
max_loss_streak: 3
avg_same_direction_count: 4.69
avg_unique_origins: 3.20
```

## 6. Interpretation

The result is promising:

```text
The train-selected confluence policies worked strongly in 2026-03, 2026-04, and 2026-05.
```

The weak 2026-06 fold has only 3 clusters and should not be overinterpreted.

The result supports the idea that:

```text
confluence is valuable;
multiple independent origin/filter signals agreeing in the same direction is stronger than treating overlaps as noise.
```

## 7. Runtime caution

The strongest top policies were stacked-mode policies.

Stacked mode assumes same-direction unit-lot addition and therefore needs strict risk limits before demo/live use.

Do not enable runtime stacking without:

```text
max stack count
max total risk per cluster
max simultaneous exposure
same-direction-only rule
opposite-conflict handling
month-by-month drawdown audit
```

## 8. Outputs

The generated audit outputs are:

```text
gold_v2_confluence_walk_forward_outputs.zip
gold_v2_confluence_walk_forward_summary.json
gold_v2_confluence_walk_forward_all_policy_folds.csv
gold_v2_confluence_walk_forward_selected_policy_folds.csv
gold_v2_confluence_walk_forward_selected_aggregate.csv
gold_v2_confluence_walk_forward_top1_test_clusters.csv
gold_v2_confluence_walk_forward_top1_summary.csv
```

## 9. Current decision

Still do not proceed to MT5 order_send or dispatch_ready.

Recommended next step:

```text
GOLD V2 full walk-forward rebuild audit
```

That stricter audit should rebuild, per fold:

```text
origin candidates
TP/SL choice
additional filters
confluence policy
```

using only train months, then test the next month.

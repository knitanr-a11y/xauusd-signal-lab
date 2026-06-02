# GOLD V2 LOW_VOL_RANGE dedicated walk-forward audit

Created: 2026-06-02
Status: AUDIT RESULT SNAPSHOT

## 1. Purpose

This document records the follow-up audit after the regime-aware walk-forward and low-vol TP/SL what-if tests.

The previous test changed TP/SL only for clusters already selected by the baseline policy. This audit is stricter for low-volatility conditions: it re-selects, using LOW_VOL_RANGE train entries only:

```text
1. candidate rules
2. TP/SL variant
3. added filters already available in the current candidate universe
4. confluence scenario
5. confluence policy
```

Then it tests only LOW_VOL_RANGE entries in the next month.

## 2. Important limitation

This is not raw-OHLC full re-mining.

It selects from the current mined GOLD V2 candidate/filter universe. Therefore this audit is stricter than merely re-pricing baseline low-vol clusters, but still less strict than full raw discovery per fold.

## 3. Input universe

Candidate/filter universe count:

```text
1040 candidate variants
13 origin candidates
```

Inputs include current GOLD V2 high-win and transformation candidates plus selected portfolio rules.

Market data:

```text
goldsharp_m15.csv
goldsharp_m5.csv
goldsharp_m1.csv
```

## 4. Regime handling

LOW_VOL_RANGE is classified using the same prototype regime classifier from the previous audit.

Important point:

```text
Regime thresholds are fitted on train months only for each fold.
Test month entries use those fixed train thresholds.
```

LOW_VOL_RANGE entry-row availability:

```text
Fold 1 train 2025-12..2026-02 -> test 2026-03:
  train low-vol rows: 514
  test low-vol rows: 80

Fold 2 train 2025-12..2026-03 -> test 2026-04:
  train low-vol rows: 989
  test low-vol rows: 425

Fold 3 train 2025-12..2026-04 -> test 2026-05:
  train low-vol rows: 1414
  test low-vol rows: 486

Fold 4 train 2025-12..2026-05 -> test 2026-06:
  train low-vol rows: 1741
  test low-vol rows: 17
```

## 5. Baseline comparison

Previous candidate-universe walk-forward baseline:

```text
baseline_all_previous:
  count: 166
  win_rate: 63.25%
  PF: 2.44
  total_r: +195.0R
  max_loss_streak: 3
  avg_monthly_count: 41.5
```

Baseline low-vol-only part:

```text
baseline_lowvol_only_previous:
  count: 23
  win_rate: 56.52%
  PF: 1.47
  total_r: +15.5R
  max_loss_streak: 3
  avg_monthly_count: 5.75
```

Baseline non-low-vol part:

```text
baseline_nonlow_previous:
  count: 143
  win_rate: 64.34%
  PF: 2.76
  total_r: +179.5R
  max_loss_streak: 3
  avg_monthly_count: 35.75
```

## 6. Low-vol dedicated results

### 6.1 Fold-best uncapped stacked low-vol policy

```text
lowvol_dedicated_only_foldbest_uncapped:
  count: 33
  win_rate: 66.67%
  PF: 4.32
  total_r: +99.5R
  max_loss_streak: 3
  avg_monthly_count: 8.25
```

Combined with baseline non-low-vol using strict no-overlap:

```text
combined_strict_foldbest_uncapped:
  count: 174
  win_rate: 64.37%
  PF: 2.99
  total_r: +263.0R
  max_loss_streak: 3
  avg_monthly_count: 43.5
```

This improves over baseline total R and PF, but the fold-best policies are uncapped stacked policies. They are not runtime-safe without explicit stack/risk caps.

### 6.2 Risk-limited capped/representative low-vol policy

A safer selection was also made using only representative/capped2/capped3 modes, excluding uncapped stacked mode.

```text
lowvol_dedicated_only_capped_or_rep:
  count: 24
  win_rate: 66.67%
  PF: 2.82
  total_r: +34.5R
  max_loss_streak: 2
  avg_monthly_count: 6.0
```

Combined with baseline non-low-vol using strict no-overlap:

```text
combined_strict_capped_or_rep:
  count: 166
  win_rate: 64.46%
  PF: 2.74
  total_r: +210.0R
  max_loss_streak: 4
  avg_monthly_count: 41.5
```

This is more realistic than uncapped stacking and still improves total R versus the baseline +195.0R.

## 7. Fold-level low-vol dedicated results

### Uncapped fold-best policies

```text
Fold 1 test 2026-03:
  scenario: LOWVOL_TOP30_ALL
  policy: stacked_min_same_count_2
  test_count: 4
  test_win_rate: 100.0%
  test_PF: inf
  test_total_r: +33.5R

Fold 2 test 2026-04:
  scenario: LOWVOL_TOP2_PER_ORIGIN
  policy: stacked_min_same_count_2
  test_count: 13
  test_win_rate: 61.54%
  test_PF: 1.97
  test_total_r: +15.5R

Fold 3 test 2026-05:
  scenario: LOWVOL_TOP30_ALL
  policy: stacked_min_same_count_1
  test_count: 15
  test_win_rate: 66.67%
  test_PF: 12.90
  test_total_r: +59.5R

Fold 4 test 2026-06:
  scenario: LOWVOL_TOP30_ALL
  policy: stacked_min_same_count_2
  test_count: 1
  test_win_rate: 0.0%
  test_PF: 0.0
  test_total_r: -9.0R
```

2026-06 has only 17 low-vol entry rows and 1 selected low-vol test cluster. It should be treated as sample-poor.

### Capped/representative selected policies

```text
Fold 1 test 2026-03:
  scenario: LOWVOL_TOP2_PER_ORIGIN
  policy: capped3_min_same_count_2
  test_count: 3
  test_win_rate: 100.0%
  test_total_r: +11.5R

Fold 2 test 2026-04:
  scenario: LOWVOL_TOP2_PER_ORIGIN
  policy: capped3_min_same_count_2
  test_count: 13
  test_win_rate: 61.54%
  test_PF: 2.29
  test_total_r: +15.5R

Fold 3 test 2026-05:
  scenario: LOWVOL_TOP30_ALL
  policy: capped3_score_sum_ge_10
  test_count: 6
  test_win_rate: 83.33%
  test_PF: 14.50
  test_total_r: +13.5R

Fold 4 test 2026-06:
  scenario: LOWVOL_TOP2_PER_ORIGIN
  policy: capped3_score_sum_ge_15
  test_count: 2
  test_win_rate: 0.0%
  test_total_r: -6.0R
```

## 8. Interpretation

The earlier low-vol TP/SL replacement test did not meaningfully improve total R. The reason is now clearer:

```text
Changing TP/SL on baseline-selected low-vol clusters is not enough.
Low-vol needs its own rule/TP-SL/policy selection.
```

Dedicated low-vol selection improves the low-vol component substantially:

```text
Baseline low-vol only:
  PF 1.47, total R +15.5R

Dedicated low-vol capped/representative:
  PF 2.82, total R +34.5R

Dedicated low-vol uncapped fold-best:
  PF 4.32, total R +99.5R
```

However, the strongest result relies on uncapped stacking, which should not be used directly in runtime.

## 9. Current decision

Recommended near-term interpretation:

```text
1. Do not disable LOW_VOL_RANGE automatically.
2. Do not merely change TP/SL for baseline low-vol clusters.
3. Build a LOW_VOL_RANGE-specific rule/policy branch.
4. Use capped/representative result as the safer benchmark.
5. Treat uncapped stacked result as an upper-bound reference only.
```

Runtime-safe low-vol policy should start with:

```text
LOW_VOL_RANGE:
  select dedicated low-vol candidates
  use capped3 or lower
  avoid uncapped stacking
  require same-direction confluence
  monitor 2026-06 and future months carefully
```

## 10. Runtime safety status

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI/API: not used
```

## 11. Generated outputs

```text
gold_v2_low_vol_dedicated_wf_outputs.zip
gold_v2_low_vol_dedicated_summary.csv
gold_v2_low_vol_dedicated_fold_summary.csv
gold_v2_low_vol_dedicated_monthly_summary.csv
gold_v2_low_vol_dedicated_rule_eval.csv
gold_v2_low_vol_dedicated_selected_rules.csv
gold_v2_low_vol_dedicated_policy_folds.csv
gold_v2_low_vol_dedicated_fold_best_policy.csv
gold_v2_low_vol_dedicated_fold_best_policy_capped_or_rep.csv
gold_v2_low_vol_dedicated_selected_clusters.csv
gold_v2_low_vol_dedicated_selected_clusters_capped_or_rep.csv
gold_v2_low_vol_dedicated_combined_clusters_strict_no_overlap.csv
gold_v2_low_vol_dedicated_combined_clusters_strict_no_overlap_capped_or_rep.csv
gold_v2_low_vol_dedicated_report.md
```

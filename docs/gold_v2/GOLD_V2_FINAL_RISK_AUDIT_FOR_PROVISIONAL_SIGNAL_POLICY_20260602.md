# GOLD V2 final risk audit for provisional signal policy

Created: 2026-06-02
Status: FINAL PRE-DRY-RUN RISK AUDIT SNAPSHOT

## 1. Purpose

This document records the risk audit for the provisional GOLD V2 signal policy before building dry-run output.

The audited provisional structure is:

```text
non-low-vol regimes:
  candidate-universe WF baseline selection

LOW_VOL_RANGE:
  dedicated low-vol candidate/policy branch

runtime safety assumption:
  no uncapped stacking
  prefer representative/capped modes
  MT5/Discord still disabled
```

## 2. Important critical finding

The adopted-as-recorded combined file uses capped/representative selection for LOW_VOL_RANGE, but the non-low-vol side still contains selected policies recorded as `stacked_same_direction_profit_r`.

Therefore:

```text
adopted_as_recorded is not fully runtime-capped.
adopted_fully_capped3_override must be used as the safer runtime proxy.
representative_only is the conservative lower-bound proxy.
```

## 3. Main variant comparison

| variant | count | win_rate | PF | total_R | max_loss_streak | max_drawdown_R | worst_cluster_R | avg_monthly_count | interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| adopted_as_recorded_lowvol_capped_nonlow_as_selected | 166 | 64.46% | 2.74 | +210.0 | 4 | 12.0 | -11.0 | 41.5 | Useful but not fully runtime-capped because non-low stacked remains. |
| adopted_fully_capped3_override | 166 | 65.06% | 2.49 | +168.5 | 4 | 12.0 | -3.0 | 41.5 | Safer runtime proxy. Max single cluster loss reduced. |
| adopted_representative_only_override | 166 | 65.06% | 2.21 | +70.0 | 4 | 4.0 | -1.0 | 41.5 | Conservative lower bound. |
| baseline_candidate_universe_selected_profit | 166 | 63.25% | 2.44 | +195.0 | 3 | 17.0 | -11.0 | 41.5 | Previous stricter baseline. |
| safe_nonstacked_skip_lowvol_or_nonstacked | 143 | 64.34% | 2.76 | +179.5 | 3 | 12.0 | -11.0 | 35.75 | Safer lower frequency reference, but still has large single loss in source profit. |
| upper_bound_uncapped_lowvol_foldbest | 174 | 64.37% | 2.99 | +263.0 | 3 | 13.0 | -11.0 | 43.5 | Upper-bound reference only. Not runtime safe. |

## 4. Adopted-as-recorded monthly risk

| month | count | win_rate | PF | total_R | max_loss_streak | max_drawdown_R | worst_cluster_R |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-03 | 64 | 75.00% | 5.13 | +111.5 | 1 | 3.0 | -3.0 |
| 2026-04 | 55 | 60.00% | 2.77 | +65.5 | 2 | 7.0 | -5.0 |
| 2026-05 | 42 | 57.14% | 1.65 | +32.0 | 4 | 12.0 | -11.0 |
| 2026-06 | 5 | 40.00% | 1.12 | +1.0 | 2 | 6.0 | -3.0 |

Interpretation:

```text
March is very strong.
April remains good.
May deteriorates materially, mainly from SELL/MID_MIXED risk.
June is sample-poor and should not be overinterpreted, but it is not strong.
```

## 5. Direction risk

| direction | count | win_rate | PF | total_R | max_loss_streak | max_drawdown_R | worst_cluster_R |
|---|---:|---:|---:|---:|---:|---:|---:|
| SELL | 112 | 67.86% | 2.95 | +163.5 | 4 | 21.0 | -11.0 |
| BUY | 54 | 57.41% | 2.26 | +46.5 | 2 | 5.0 | -3.0 |

Interpretation:

```text
SELL contributes most profit but also most tail risk.
BUY is less profitable but materially reduces one-sided SELL dependency and should not be removed.
```

## 6. Regime risk

| regime | count | win_rate | PF | total_R | max_loss_streak | max_drawdown_R | worst_cluster_R |
|---|---:|---:|---:|---:|---:|---:|---:|
| MID_MIXED | 71 | 60.56% | 2.14 | +76.5 | 3 | 12.0 | -11.0 |
| HIGH_VOL_TREND | 46 | 67.39% | 3.43 | +56.0 | 2 | 3.0 | -3.0 |
| HIGH_VOL_CHOP | 26 | 69.23% | 4.92 | +47.0 | 2 | 5.0 | -3.0 |
| LOW_VOL_RANGE | 23 | 65.22% | 2.61 | +30.5 | 2 | 6.0 | -3.0 |

Interpretation:

```text
LOW_VOL_RANGE improved after dedicated branch.
High-vol regimes are already strong and do not need a dedicated branch now.
MID_MIXED is the main risk bucket because it contains the -11R cluster.
```

## 7. Direction x regime issue

Important bucket:

```text
SELL + MID_MIXED:
  count 48
  win_rate 66.67%
  PF 2.18
  total_R +56.5
  worst_cluster_R -11.0
```

The bucket is profitable, but it contains the largest tail loss.

## 8. Worst clusters

Key worst clusters in adopted-as-recorded:

| cluster_start | month | direction | candidate | variant | regime | policy | profit_R | same_direction_count | unique_origins |
|---|---|---|---|---|---|---|---:|---:|---:|
| 2026-05-01 15:30 | 2026-05 | SELL | GOLDV2_ORIGIN_010 | SELL_TP150_SL150_RR1p0 | MID_MIXED | stacked_no_conflict_min_same_count_2 | -11.0 | 11 | 7 |
| 2026-04-13 04:15 | 2026-04 | SELL | GOLDV2_ORIGIN_010 | SELL_TP125_SL125_RR1p0 | MID_MIXED | stacked_no_conflict_min_same_count_2 | -5.0 | 5 | 4 |
| 2026-05-28 17:45 | 2026-05 | SELL | GOLDV2_ORIGIN_001 | SELL_TP150_SL150_RR1p0 | MID_MIXED | stacked_no_conflict_min_same_count_2 | -4.0 | 4 | 2 |
| 2026-06-02 07:00 | 2026-06 | SELL | GOLDV2_ORIGIN_004 | SELL_TP225_SL150_RR1p5 | LOW_VOL_RANGE | capped3_score_sum_ge_15 | -3.0 | 8 | 4 |
| 2026-06-02 05:30 | 2026-06 | SELL | GOLDV2_ORIGIN_005 | SELL_TP150_SL150_RR1p0 | LOW_VOL_RANGE | capped3_score_sum_ge_15 | -3.0 | 4 | 3 |

Runtime implication:

```text
The main threat is not many small losses. It is same-direction clustered SELL failure.
Fully capped3 reduces worst single cluster loss from -11R to -3R.
```

## 9. Loss streaks

Worst consecutive loss sequence:

```text
2026-05-06 18:00 -> 2026-05-08 07:45
count: 4
total_R: -8.0
regimes: HIGH_VOL_TREND / LOW_VOL_RANGE / MID_MIXED
directions: BUY and SELL
```

Other notable sequences:

```text
2026-05-28 16:00 -> 2026-05-28 17:45: 2 losses, -7.0R
2026-06-02 05:30 -> 2026-06-02 07:00: 2 losses, -6.0R
2026-04-23 14:15 -> 2026-04-23 15:00: 2 losses, -5.0R
```

## 10. Stack-count risk

Stack-count buckets show that confluence generally helps, but high confluence does not guarantee safety.

```text
same_direction_count=11:
  count 1
  win_rate 0%
  total_R -11.0

same_direction_count=8:
  count 1
  win_rate 0%
  total_R -3.0

same_direction_count=10:
  count 4
  win_rate 75%
  PF 11.5
  total_R +10.5
```

Interpretation:

```text
More confluence usually improves quality, but rare high-confluence failure can be expensive.
Runtime must cap stack count.
```

## 11. Recommendation before dry-run policy build

Use this as the next dry-run benchmark:

```text
adopted_fully_capped3_override:
  count 166
  win_rate 65.06%
  PF 2.49
  total_R +168.5
  max_loss_streak 4
  max_drawdown_R 12.0
  worst_cluster_R -3.0
```

Keep these for comparison:

```text
representative_only:
  PF 2.21
  total_R +70.0
  worst_cluster_R -1.0

adopted_as_recorded:
  PF 2.74
  total_R +210.0
  worst_cluster_R -11.0
```

Recommended runtime rule draft:

```text
1. max_stack_count <= 3
2. same-direction only
3. no opposite conflict
4. LOW_VOL_RANGE uses dedicated branch
5. MID_MIXED SELL should be monitored as tail-risk bucket
6. uncapped stacked mode is prohibited
7. dispatch_ready remains false
```

## 12. Decision

The provisional system is still viable, but the actual dry-run policy should be capped.

Do not use the adopted-as-recorded result as a runtime risk model because it still contains non-low uncapped stacked profits.

Proceed to provisional signal policy build using:

```text
primary dry-run risk model: fully capped3 override
secondary conservative benchmark: representative-only
```

## 13. Runtime status

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI/API: not used
uncapped stacking: prohibited
```

## 14. Local output bundle

Generated local files:

```text
gold_v2_final_risk_audit_outputs.zip
gold_v2_final_risk_audit_report.md
gold_v2_final_risk_summary_by_variant.csv
gold_v2_final_risk_breakdowns_adopted_as_recorded.csv
gold_v2_final_risk_breakdowns_adopted_fully_capped3.csv
gold_v2_final_risk_breakdowns_representative_only.csv
gold_v2_final_risk_time_buckets_adopted.csv
gold_v2_final_risk_worst_clusters_adopted_as_recorded.csv
gold_v2_final_risk_worst_clusters_adopted_fully_capped3.csv
gold_v2_final_risk_loss_streak_sequences_adopted.csv
gold_v2_final_risk_uncapped_stack_rows_in_adopted_as_recorded.csv
```

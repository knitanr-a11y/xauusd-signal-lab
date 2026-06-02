# GOLD V2 regime-aware and low-vol TP/SL audit

Created: 2026-06-02
Status: AUDIT RESULT SNAPSHOT

## 1. Purpose

This document records the GOLD V2 regime-aware walk-forward audit and the follow-up low-volatility TP/SL what-if audit.

The motivation was that the candidate-universe walk-forward result deteriorated from earlier optimistic confluence results, especially in later months. A likely cause was market regime change: lower volatility and more range-like behavior.

## 2. Important principle

Regime classification must not use hindsight monthly labels.

Runtime-style classification must use only data available at entry time.

Therefore, this audit classifies each entry/cluster using confirmed M15 features available at the cluster entry time.

## 3. Regime classifier prototype

The prototype uses train-fold thresholds and applies them to the next test month.

Features:

```text
ATR14
M15 true-range mean over recent bars
recent 96-bar range
recent 192-bar range
trend efficiency over recent 96 bars
ADX14
recent 96-bar return
```

Regime labels:

```text
LOW_VOL_RANGE
MID_MIXED
HIGH_VOL_TREND
HIGH_VOL_CHOP
UNKNOWN
```

For each fold, thresholds are estimated from train months only, then fixed for the test month.

## 4. Baseline candidate-universe walk-forward

Previous stricter candidate-universe rebuild walk-forward:

```text
count: 166
win_rate: 63.25%
PF: 2.44
total_r: +195.0R
max_loss_streak: 3
avg_monthly_count: 41.5
```

## 5. Regime split of the baseline clusters

The baseline selected clusters split by regime as follows:

```text
HIGH_VOL_CHOP:
  count: 26
  win_rate: 69.2%
  PF: 4.92
  total_r: +47.0R

HIGH_VOL_TREND:
  count: 46
  win_rate: 67.4%
  PF: 3.43
  total_r: +56.0R

MID_MIXED:
  count: 71
  win_rate: 60.6%
  PF: 2.14
  total_r: +76.5R

LOW_VOL_RANGE:
  count: 23
  win_rate: 56.5%
  PF: 1.47
  total_r: +15.5R
```

Interpretation:

```text
LOW_VOL_RANGE is weaker than high-vol regimes, but still positive.
```

## 6. Simple regime gate what-if

Simple what-if result:

```text
baseline_all:
  count: 166
  win_rate: 63.3%
  PF: 2.44
  total_r: +195.0R

skip_low_vol_range:
  count: 143
  win_rate: 64.3%
  PF: 2.76
  total_r: +179.5R

only_high_vol:
  count: 72
  win_rate: 68.1%
  PF: 3.94
  total_r: +103.0R

only_low_vol_range:
  count: 23
  win_rate: 56.5%
  PF: 1.47
  total_r: +15.5R
```

Interpretation:

```text
Skipping low-vol improves PF but lowers total R.
High-vol-only is clean but reduces opportunity.
Low-vol should not automatically be disabled because it remains positive.
```

## 7. Low-vol alternate TP/SL what-if

A follow-up what-if recomputed M1 first-touch outcomes only for LOW_VOL_RANGE clusters while keeping non-low-vol clusters unchanged.

Tested examples:

```text
LOW_VOL TP50/SL50 with stack cap 1/2/3
LOW_VOL TP75/SL75 with stack cap 1/2/3
LOW_VOL TP100/SL75 with stack cap 1/2/3
LOW_VOL TP100/SL100 with stack cap 1/2/3
LOW_VOL TP75/SL50 with stack cap 1/2/3
LOW_VOL TP50/SL25 with stack cap 1/2
```

Important finding:

```text
Changing low-vol TP/SL did not improve total R versus the baseline.
Some variants slightly improved PF, but mostly by reducing exposure and total R.
```

Best PF example among tested alternate TP/SL variants:

```text
lowvol_tp100_sl100_cap1:
  total count: 166
  win_rate: 63.25%
  PF: 2.63
  total_r: +182.5R
  max_loss_streak: 3
```

Baseline:

```text
baseline_all:
  count: 166
  win_rate: 63.25%
  PF: 2.44
  total_r: +195.0R
  max_loss_streak: 3
```

Therefore:

```text
low-vol alternate TP/SL improved PF slightly in some cases,
but did not improve total R.
```

## 8. Low-vol original TP/SL with stack cap only

Additional test: keep original TP/SL but reduce low-vol stack count.

```text
baseline_all:
  win_rate: 63.25%
  PF: 2.44
  total_r: +195.0R
  max_loss_streak: 3

lowvol_original_cap1:
  win_rate: 62.05%
  PF: 2.57
  total_r: +179.0R
  max_loss_streak: 5

lowvol_original_cap2:
  win_rate: 62.65%
  PF: 2.55
  total_r: +185.5R
  max_loss_streak: 5

lowvol_original_cap3:
  win_rate: 62.65%
  PF: 2.59
  total_r: +192.0R
  max_loss_streak: 5
```

Interpretation:

```text
Stack cap and TP/SL changes can raise PF slightly, but not enough to beat baseline total R.
The safest interpretation is not to switch low-vol TP/SL blindly.
```

## 9. Current decision

Do not implement full regime switching yet.

The safer near-term rule is:

```text
HIGH_VOL_TREND / HIGH_VOL_CHOP:
  allow normal confluence
  allow wider TP/SL
  stack cap may be up to 3 after further DD checks

MID_MIXED:
  standard policy
  stack cap 2 or 3 depending on drawdown

LOW_VOL_RANGE:
  do not disable automatically
  do not blindly shrink TP/SL
  prefer risk reduction / stricter confluence threshold
  consider cap 1-2 only after drawdown analysis
```

## 10. Runtime safety status

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI/API: not used
```

## 11. Generated local outputs

Regime-aware walk-forward:

```text
gold_v2_regime_aware_walk_forward_outputs.zip
gold_v2_regime_wf_final_report.md
gold_v2_regime_wf_simple_regime_gate_whatif.csv
gold_v2_regime_wf_previous_policy_regime_performance.csv
gold_v2_regime_wf_thresholds_by_fold.csv
gold_v2_regime_wf_all_clusters_with_regime.csv
```

Low-vol alternate TP/SL what-if:

```text
gold_v2_low_vol_alt_tpsl_outputs.zip
gold_v2_low_vol_alt_tpsl_summary.csv
gold_v2_low_vol_alt_tpsl_by_regime.csv
gold_v2_low_vol_alt_tpsl_monthly.csv
gold_v2_low_vol_alt_tpsl_cluster_ledger.csv
gold_v2_low_vol_original_tpsl_stackcap_summary.csv
```

# GOLD V2 CoreB RR125_BUY_CONFLUENCE exact source rules

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

This document records the exact 12 CoreB source rule rows extracted from:

```text
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv
```

It exists because writing only `RR125_from_RR1_rules + same_count>=15` is not sufficient to reimplement CoreB.  
A live evaluator must use these explicit source rule conditions, or stop with `UNMAPPED_SOURCE_RULE_CONDITIONS`.

---

## 0. CoreB adopted policy

```text
component = HIGH_B_CoreB_RR125_BUY_CONFLUENCE
policy = RR125_from_RR1_rules
filter = same_count>=15
direction = BUY only
TP = 1.25 * SL
sizing = CAP3
priority = HIGH_B
lot_multiplier_candidate = 1.0
```

---

## 1. Important caveat about same_count

`same_count>=15` was selected from `rr125_top_ledgers.csv`.

Do not assume `same_count` is simply the number of `rr125_raw_signal_ledger.csv` rows with the exact same `entry_time`. A quick audit showed exact timestamp raw-row counts do **not** match the `same_count` column in `rr125_top_ledgers.csv`.

Therefore, before CoreB can be live-evaluated, same_count must be reproduced from the same clustering / top-ledger construction used during the RR125 probe.

Until that clustering logic is mapped exactly:

```text
CoreB status = UNMAPPED_SAME_COUNT_SOURCE
signal_eligible = false
```

---

## 2. Exact 12 source rule rows

Each row is:

```text
base_condition AND added_filter_text
```

with the listed BUY variant.

### Rule 1

```text
candidate_id = GOLDV2_ORIGIN_003
origin_id = ORIGIN_003
direction = BUY
variant = BUY_TP187.5_SL150_RR1p25
tp_pips = 187.5
sl_pips = 150.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.39005 AND donch_pos_96 > 0.767993 AND donch_pos_48 > 0.661097
added_filter_text = range_144_atr <= 17.5331 AND dist_low_24_atr > 7.2163
train_score = 4.602050004454746
```

### Rule 2

```text
candidate_id = GOLDV2_ORIGIN_003
origin_id = ORIGIN_003
direction = BUY
variant = BUY_TP187.5_SL150_RR1p25
tp_pips = 187.5
sl_pips = 150.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.39005 AND donch_pos_96 > 0.767993 AND donch_pos_48 > 0.661097
added_filter_text = range_72_atr <= 8.12354 AND ret_72_atr <= 5.48496
train_score = 4.5793147929668345
```

### Rule 3

```text
candidate_id = GOLDV2_ORIGIN_003
origin_id = ORIGIN_003
direction = BUY
variant = BUY_TP187.5_SL150_RR1p25
tp_pips = 187.5
sl_pips = 150.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.39005 AND donch_pos_96 > 0.767993 AND donch_pos_48 > 0.661097
added_filter_text = range_96_atr <= 11.8934 AND ret_4_atr > 0.546479
train_score = 4.368698114832711
```

### Rule 4

```text
candidate_id = GOLDV2_ORIGIN_003
origin_id = ORIGIN_003
direction = BUY
variant = BUY_TP187.5_SL150_RR1p25
tp_pips = 187.5
sl_pips = 150.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.39005 AND donch_pos_96 > 0.767993 AND donch_pos_48 > 0.661097
added_filter_text = upper_wick_atr > 0.0892182 AND range_96_atr <= 11.8934
train_score = 4.31489511803756
```

### Rule 5

```text
candidate_id = GOLDV2_ORIGIN_007
origin_id = ORIGIN_007
direction = BUY
variant = BUY_TP187.5_SL150_RR1p25
tp_pips = 187.5
sl_pips = 150.0
rr = 1.25
base_condition = ema100_slope_4_atr > 0.21561 AND ret_96_atr > 2.12313 AND compression_range_32_96 > 0.302005 AND dist_low_96_atr > 8.30197
added_filter_text = dist_low_144_atr <= 20.1393 AND abs_ret_48_atr > 10.7678
train_score = 5.237268689806819
```

### Rule 6

```text
candidate_id = GOLDV2_ORIGIN_007
origin_id = ORIGIN_007
direction = BUY
variant = BUY_TP187.5_SL150_RR1p25
tp_pips = 187.5
sl_pips = 150.0
rr = 1.25
base_condition = ema100_slope_4_atr > 0.21561 AND ret_96_atr > 2.12313 AND compression_range_32_96 > 0.302005 AND dist_low_96_atr > 8.30197
added_filter_text = dist_low_144_atr <= 20.1393 AND ret_48_atr > 10.7678
train_score = 5.237268689806819
```

### Rule 7

```text
candidate_id = GOLDV2_ORIGIN_008
origin_id = ORIGIN_008
direction = BUY
variant = BUY_TP31.25_SL25_RR1p25
tp_pips = 31.25
sl_pips = 25.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.10701 AND donch_pos_96 > 0.767993 AND ret_96_atr > 4.68457
added_filter_text = dist_low_96_atr <= 9.51537 AND compression_range_48_144 > 0.680757
train_score = 4.815516915862178
```

### Rule 8

```text
candidate_id = GOLDV2_ORIGIN_008
origin_id = ORIGIN_008
direction = BUY
variant = BUY_TP31.25_SL25_RR1p25
tp_pips = 31.25
sl_pips = 25.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.10701 AND donch_pos_96 > 0.767993 AND ret_96_atr > 4.68457
added_filter_text = range_96_atr <= 11.6688 AND compression_range_48_144 > 0.680757
train_score = 4.727895802539815
```

### Rule 9

```text
candidate_id = GOLDV2_ORIGIN_008
origin_id = ORIGIN_008
direction = BUY
variant = BUY_TP31.25_SL25_RR1p25
tp_pips = 31.25
sl_pips = 25.0
rr = 1.25
base_condition = abs_ret_72_atr > 4.10701 AND donch_pos_96 > 0.767993 AND ret_96_atr > 4.68457
added_filter_text = range_96_atr <= 11.6688 AND m5_compression_range_16_96 <= 0.273431
train_score = 4.582503493227244
```

### Rule 10

```text
candidate_id = GOLDV2_ORIGIN_012
origin_id = ORIGIN_012
direction = BUY
variant = BUY_TP156.25_SL125_RR1p25
tp_pips = 156.25
sl_pips = 125.0
rr = 1.25
base_condition = ret_144_atr > 5.98421 AND donch_pos_144 > 0.811696 AND abs_ret_144_atr <= 22.2508 AND dist_high_144_atr <= 2.5037
added_filter_text = compression_range_32_96 > 0.679222 AND m5_dist_low_32_atr <= 3.83896
train_score = 4.97532979092393
```

### Rule 11

```text
candidate_id = GOLDV2_ORIGIN_012
origin_id = ORIGIN_012
direction = BUY
variant = BUY_TP156.25_SL125_RR1p25
tp_pips = 156.25
sl_pips = 125.0
rr = 1.25
base_condition = ret_144_atr > 5.98421 AND donch_pos_144 > 0.811696 AND abs_ret_144_atr <= 22.2508 AND dist_high_144_atr <= 2.5037
added_filter_text = dist_low_32_atr > 8.48382 AND m5_abs_ret_96_atr > 14.267
train_score = 5.370134845626629
```

### Rule 12

```text
candidate_id = GOLDV2_ORIGIN_012
origin_id = ORIGIN_012
direction = BUY
variant = BUY_TP156.25_SL125_RR1p25
tp_pips = 156.25
sl_pips = 125.0
rr = 1.25
base_condition = ret_144_atr > 5.98421 AND donch_pos_144 > 0.811696 AND abs_ret_144_atr <= 22.2508 AND dist_high_144_atr <= 2.5037
added_filter_text = dist_low_32_atr > 8.48382 AND m5_ret_96_atr > 14.267
train_score = 5.370134845626629
```

---

## 3. RR1.25 conversion rule

The source rows above are RR1.25 rows generated from RR1.0-derived BUY rules.

For each source BUY rule:

```text
entry condition = base_condition AND added_filter_text
SL = sl_pips
TP = 1.25 * sl_pips
variant = BUY_TP{1.25*SL}_SL{SL}_RR1p25
```

No SELL conversion is allowed.

---

## 4. Required future evaluator behavior

A CoreB live evaluator must:

1. Calculate all listed feature fields exactly.
2. Evaluate all 12 `base_condition AND added_filter_text` rows.
3. Convert each hit to an RR1.25 BUY candidate using the listed `sl_pips` and `tp_pips`.
4. Reproduce the same same_count clustering/top-ledger logic used by `rr125_top_ledgers.csv`.
5. Keep only candidates satisfying the adopted filter:

```text
filter = same_count>=15
```

If step 4 is not fully mapped:

```text
CoreB status = UNMAPPED_SAME_COUNT_SOURCE
signal_eligible = false
```

---

## 5. Required future source files

At minimum:

```text
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
rr125_filter_results.csv
rr125_recommended_filters.csv
```

The exact source rule rows are in:

```text
rr125_raw_signal_ledger.csv
columns:
  policy
  candidate_id
  origin_id
  direction
  variant
  tp_pips
  sl_pips
  rr
  rr_bucket
  base_condition
  added_filter_text
  train_score
  entry_time
  entry_price
  exit_time
  profit_r
```

The selected filter result is in:

```text
rr125_filter_results.csv
row:
  policy = RR125_from_RR1_rules
  filter = same_count>=15
```

The top-ledger selected clusters are in:

```text
rr125_top_ledgers.csv
columns:
  cluster_id
  entry_time
  entry_month
  profit
  top_direction
  same_count
  unique_origins
  top_candidate_id
  rr_bucket
  source_rule_count
  dataset
  policy
  filter
```

---

## 6. Still unresolved

This document fixes the missing 12 source rules, but the following is still not fully specified:

```text
- Exact feature-generation formulas for all *_atr / donch_pos / compression / m5_* fields.
- Exact M15/M5 merge/asof timing.
- Exact top-ledger clustering algorithm that produced same_count.
```

Until those are found from the original exploration script or recreated with exact tests against the ledgers, CoreB live evaluation must stop before producing a signal.

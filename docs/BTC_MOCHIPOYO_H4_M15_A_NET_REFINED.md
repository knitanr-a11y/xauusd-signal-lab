# BTC_MOCHIPOYO_H4_M15_A_NET_REFINED

## Status

`BTC_MOCHIPOYO_H4_M15_A_NET_REFINED` is the current provisional leading BTC Mochipoyo candidate.

This is **not** a live-notification preset yet.
This is **not** an AI-review target yet.

BTC must be judged by spread-aware net performance. Gross-only results are reference only.

## Core conclusion

The full BTC Mochipoyo scan was not acceptable after spread.

Full BTC Mochipoyo RR1.2 after M1/M5 touch-range filtering:

```text
trades: 2095
wins: 764
losses: 887
timeouts: 444
net_total_r: -178.74R
net_pf: 0.798
net_max_dd_r: 189.94R
max_consecutive_losses: 11
mode_spread_points: 2250
mode_spread_price: 22.5
avg_spread_to_sl_ratio: 0.1287
avg_effective_rr_after_spread: 0.9698
```

Therefore, the broad BTC Mochipoyo set is rejected.

The only useful branch found so far is:

```text
BTC_H4_M15_DAYTRADE
candidate_rank A
BUY and SELL
spread-aware net refined filters
```

## Mandatory BTC rules

This candidate is valid only under these rules:

```text
context_close_time <= base_close_time
pivot_confirmed_time <= signal_close_time
entry_time >= signal_close_time
same-bar TP/SL ambiguity uses SL priority
BTC selection uses net_r_after_spread, not gross_r_result
spread is taken from CSV mode spread points unless explicitly overridden
```

BTC gross performance must never be used as adoption evidence by itself.

## Candidate generation

BTC was scanned with the same Mochipoyo logic as GOLD:

```text
EMA20/30/40 order
Granville 2/3 buy/sell zones
ZigZag pullback/retrace structure
MACD 6/13/4 divergence or hidden divergence
RCI 9/14/18 zone and turn conditions
confirmed-time MTF join
```

Full BTC timeframe pairs considered:

```text
BTC_M15_M1_SUPER_SCALP
BTC_H1_M5_SCALP
BTC_H4_M15_DAYTRADE
BTC_D1_H1_DAYTRADE
```

Candidate scan audit passed:

```text
context_leak_violations: 0
base_pivot_leak_violations: 0
context_pivot_leak_violations: 0
entry_timing_violations: 0
```

Full candidate-state counts:

```text
BTC_M15_M1_SUPER_SCALP: 90304
BTC_H4_M15_DAYTRADE: 19525
BTC_H1_M5_SCALP: 18974
BTC_D1_H1_DAYTRADE: 12426
```

After event filtering:

```text
input_rows: 141229
rows_after_basic_filters: 125436
rows_after_cooldown: 4285
output_rows: 3151
```

After touch-range filtering:

```text
input_rows: 3151
output_rows: 2095
dropped_rows: 1056
reason: before_M5_history
```

## Spread-aware BTC first-touch settings

BTC backtest script:

```text
scripts/backtest_mochipoyo_btc_events_spread_first_touch.py
```

Settings used:

```text
RR: 1.2
spread_source: M1_mode
mode_spread_points: 2250
mode_spread_price: 22.5
point_size: 0.01
BTC pip conversion for summary: 10 dollars = 1 pip
same-candle TP/SL: SL priority
```

Net result formula used by BTC backtest:

```text
WIN: effective_rr_after_spread
LOSS: -1R
TIMEOUT: 0R
```

Where:

```text
effective_rr_after_spread = (RR * gross_risk - spread_price) / (gross_risk + spread_price)
```

## First positive net slices

Positive H4/M15 A slices before refinement:

```text
BTC_H4_M15_DAYTRADE|A|SELL
trades: 94
win_rate: 56.41%
net_total_r: +12.35R
net_pf: 1.36
net_max_dd_r: 8.42R
avg_spread_to_sl_ratio: 0.0600
avg_effective_rr_after_spread: 1.0845

BTC_H4_M15_DAYTRADE|A|BUY
trades: 68
win_rate: 54.72%
net_total_r: +5.76R
net_pf: 1.24
net_max_dd_r: 6.00R
avg_spread_to_sl_ratio: 0.0636
avg_effective_rr_after_spread: 1.0771
```

Combined pre-refinement H4/M15 A only:

```text
trades: 162
wins: 73
losses: 58
timeouts: 31
win_rate: 55.73%
net_total_r: +18.11R
net_pf: 1.312
net_max_dd_r: 6.69R
max_consecutive_losses: 4
avg_spread_to_sl_ratio: 0.0615
avg_effective_rr_after_spread: 1.0814
```

## Refinement

Refinement script:

```text
scripts/refine_mochipoyo_btc_net_filters.py
```

Refinement used:

```text
reason_token
total_score
context_score
base_score
spread_to_sl_ratio
effective_rr_after_spread
```

Important strong filters included examples like:

```text
total_score>=10.0
base_score>=4.0
base_ema_bear|total_score>=9.0
total_score>=11.0
```

A 20-filter refined portfolio was then built and fixed.

## Fixed preset

Fixed preset JSON:

```text
config/mochipoyo/btc_mochipoyo_h4_m15_a_net_refined_fixed_filters.json
```

Fixed-preset build command:

```cmd
python scripts/build_mochipoyo_btc_portfolio_from_fixed_preset.py --backtest-csv data/results/mochipoyo/btc_selected/btc_mochipoyo_positive_net_monthly_validated_passed_trades.csv --preset-json config/mochipoyo/btc_mochipoyo_h4_m15_a_net_refined_fixed_filters.json --output-prefix data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset
```

Fixed-preset reconstruction result:

```text
candidate_name: BTC_MOCHIPOYO_H4_M15_A_NET_REFINED
input_trades: 162
fixed_filters: 20
matched_filter_parts_rows: 662
union_exact_deduped_rows: 123
final_rows: 123
removed_rows: 0
```

## Final fixed-preset performance

```text
trades: 123
resolved: 95
wins: 59
losses: 36
timeouts: 28
win_rate: 62.11%
net_total_r: +26.38R
net_avg_r: +0.214R
net_pf: 1.733
net_max_dd_r: 4.0R
max_consecutive_losses: 4
avg_spread_to_sl_ratio: 0.0539
avg_effective_rr_after_spread: 1.0948
avg_gross_sl_distance_price: 1012.49
gross_total_r: +34.8R
gross_pf: 1.967
```

Gross is reference only. Net is the adoption metric.

## Monthly performance

```text
2026-01: 17 trades / +6.66R / net PF3.22 / DD1.0R
2026-02: 40 trades / +10.37R / net PF1.94 / DD3.0R
2026-03: 25 trades / +2.20R / net PF1.22 / DD2.0R
2026-04: 38 trades / +5.11R / net PF1.43 / DD4.0R
2026-05: 3 trades / +2.04R / DD0.0R
```

All reviewed months are positive. March is weak but not negative.

## Price-width / pips summary

BTC conversion used for this project:

```text
10 dollars = 1 pip
```

Fixed-preset BTC price-width summary:

```text
trades: 123
total_dollars: +16445.54 dollars
total_pips: +1644.55 pips
avg_dollars: +133.70 dollars/trade
avg_pips: +13.37 pips/trade
PF by dollars: 1.512
max_dd: 8850.40 dollars / 885.04 pips
max_consecutive_losses: 4
```

This is price-move summary, not lot-size monetary PnL.

## Important generated files

```text
data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset_final_portfolio.csv
data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset_by_month.csv
data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset_filter_coverage.csv
data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset_summary.json
```

Gold/BTC pips summary files:

```text
data/results/mochipoyo/mochipoyo_gold_btc_pips_summary.csv
data/results/mochipoyo/mochipoyo_gold_btc_pips_summary_by_month.csv
data/results/mochipoyo/mochipoyo_gold_btc_pips_summary.summary.json
```

## Known strengths

- Spread-aware net positive.
- All reviewed months positive.
- Low net DD: 4.0R.
- Max consecutive losses: 4.
- Average spread-to-SL ratio reduced to about 0.054 after refinement.
- Fixed-filter preset removes leaderboard re-ranking instability.

## Known weaknesses

- Review window is short and starts around 2026-01 for M1/M5 touch data.
- March is weak.
- Final trades are only 123 rows, so sample size is still moderate.
- Filters were selected from the same available backtest window, so overfitting risk remains.
- BTC must remain separate from GOLD in validation.
- Not ready for notification yet.

## Required next checks

Before notification or AI review:

1. Run a timing audit on the fixed-preset final portfolio.
2. Manually inspect representative WIN/LOSS/TIMEOUT rows.
3. Freeze raw input CSV snapshot or record row ranges for reproducibility.
4. Optionally test different RR values after the fixed candidate is documented.
5. Keep gross-only metrics out of adoption decisions.

## Decision

```text
BTC_MOCHIPOYO_H4_M15_A_NET_REFINED = provisional leading BTC Mochipoyo candidate
```

Not allowed yet:

```text
live notification
AI review automation
mixing with GOLD as one unvalidated live portfolio
```

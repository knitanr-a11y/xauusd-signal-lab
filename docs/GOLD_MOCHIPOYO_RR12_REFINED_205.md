# GOLD_MOCHIPOYO_RR12_REFINED

## Status

`GOLD_MOCHIPOYO_RR12_REFINED` is the current provisional leading GOLD candidate.

The old working name was `GOLD_MOCHIPOYO_RR12_REFINED_205`. The candidate name is now **condition-based instead of row-count-based**, because future MT5 CSV updates can legitimately add new rows while preserving the same fixed-filter logic.

This is **not** a live-notification preset yet.
This is **not** an AI-review target yet.
This candidate must remain in the review/backtest stage until the final trade CSV, fixed-preset regeneration path, and timing audit are manually checked.

## Fixed-filter reproduction rule

This candidate must now be reproduced from the fixed preset:

```text
config/mochipoyo/gold_mochipoyo_rr12_refined_fixed_filters.json
```

Do **not** reselect leaderboard top filters during normal reproduction.

Correct fixed-preset build command:

```cmd
python scripts/build_mochipoyo_portfolio_from_fixed_preset.py --backtest-csv data/results/mochipoyo/selected/gold_mochipoyo_passed_backtest_rr12.csv --preset-json config/mochipoyo/gold_mochipoyo_rr12_refined_fixed_filters.json --output-prefix data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset
```

Expected fixed-preset review result from the reference run:

```text
fixed_filters: 20
matched_filter_parts_rows: 767
union_exact_deduped_rows: 265
portfolio_before_exclusions_rows: 224
removed_rows: 19
final_rows: 205
```

Final fixed-preset CSV:

```text
data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_final_portfolio.csv
```

## Core idea

This candidate translates the Mochipoyo-style guide into a reproducible backtest flow:

1. Use the higher timeframe to identify buy/sell zones.
2. Prefer Granville buy/sell 2 and 3, especially type 3 pullback/retrace continuation.
3. Use EMA20/EMA30/EMA40 for trend direction and pullback/retrace location.
4. Use RCI 9/14/18 for zone and turn confirmation.
5. Use MACD 6/13/4 divergence or hidden divergence as an additional reason.
6. Drop to the lower timeframe for timing.
7. Convert persistent good environments into event candidates before first-touch testing.
8. Apply the fixed 20-filter preset and configured weak-slice exclusion.

## Mandatory anti-leak rules

This candidate is valid only if all of the following remain true:

```text
context_close_time <= base_close_time
pivot_confirmed_time <= signal_close_time
entry_time >= signal_close_time
outcome bars start at or after entry_time
same-bar TP/SL ambiguity uses SL priority
```

Bar start-time joins are not allowed. Higher timeframe rows must be joined by confirmed close time.

The earlier candidate-generation audits showed zero timing violations:

```text
context_leak_violations: 0
base_pivot_leak_violations: 0
context_pivot_leak_violations: 0
entry_timing_violations: 0
```

## Input CSVs

GOLD MT5 export files:

```text
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

The final review window is limited by M1/M5 history starting around `2025-11-28`.
Older higher-timeframe candidates were filtered out if touch data was unavailable.

## Scripts used

```text
scripts/scan_mochipoyo_multi_tf_candidates.py
scripts/filter_mochipoyo_candidate_events.py
scripts/filter_mochipoyo_events_by_touch_range.py
scripts/backtest_mochipoyo_gold_events_first_touch.py
scripts/analyze_mochipoyo_gold_backtest_slices.py
scripts/extract_mochipoyo_positive_slices.py
scripts/validate_mochipoyo_selected_monthly.py
scripts/refine_mochipoyo_gold_rr12_filters.py
scripts/build_mochipoyo_refined_portfolio.py
scripts/sweep_mochipoyo_refined_portfolio.py
scripts/exclude_mochipoyo_portfolio_slices.py
scripts/make_mochipoyo_fixed_filter_preset.py
scripts/build_mochipoyo_portfolio_from_fixed_preset.py
```

## Timeframe pairs considered

```text
GOLD_H1_M1_SCALP
GOLD_H4_M5_SCALP
GOLD_H4_M15_DAYTRADE
GOLD_D1_H1_DAYTRADE
```

Useful pairs after refinement:

```text
GOLD_H4_M5_SCALP
GOLD_H4_M15_DAYTRADE
GOLD_D1_H1_DAYTRADE
```

`GOLD_H1_M1_SCALP|B|SELL` was excluded earlier because the monthly positive ratio was too weak.

## First-touch settings

```text
symbol: GOLD
RR: 1.2
H1 x M1: M1 first-touch
other GOLD pairs: M5 first-touch
SL: recent swing high/low on the touch timeframe
TP: entry +/- RR * risk_distance
timeout: 0R
same-candle TP/SL: SL priority
```

RR comparison on the 684 selected trades:

```text
RR1.0: +42.0R / PF1.153 / DD20.0R / max loss streak 6
RR1.2: +43.8R / PF1.151 / DD19.4R / max loss streak 7
RR1.5: +28.5R / PF1.092 / DD31.0R / max loss streak 11
```

RR1.2 was kept as the best balance before refinement.

## Refinement path

```text
candidate states: 259,397
filtered events: 4,105
M1/M5 touch-range valid events: 2,364
positive selected trades before RR refinement: 684
refined portfolio before weak-slice removal: 224
final reference candidate after weak-slice removal: 205
```

A later raw-CSV regeneration produced 206 rows because one additional valid historical row appeared in the updated MT5 CSV set. The shared 205 rows matched on common columns. For stable reproduction, use the fixed-filter preset rather than row-count naming.

## Removed weak slice

The fixed preset excludes:

```text
GOLD_H4_M15_DAYTRADE|A|SELL
```

Reference removed-slice stats:

```text
trades: 19
wins: 7
losses: 8
timeouts: 4
win_rate_resolved: 46.67%
total_r: +0.4R
PF: 1.05
max_dd_r: 5.0R
max_consecutive_losses: 5
```

Removing it improved PF and DD while barely reducing total R.

## Final fixed-preset reference performance

`GOLD_MOCHIPOYO_RR12_REFINED` reference run:

```text
trades: 205
resolved: 182
wins: 107
losses: 75
timeouts: 23
no_data: 0
win_rate_resolved: 58.79%
total_r: +53.4R
avg_r: +0.260R
PF: 1.712
max_dd_r: 4.8R
max_consecutive_losses: 4
```

## Monthly performance

```text
2025-12: 24 trades / +12.2R / PF2.74 / DD3.0R
2026-01: 35 trades / +14.2R / PF2.29 / DD2.0R
2026-02: 36 trades / +13.2R / PF2.10 / DD3.8R
2026-03: 57 trades / +4.0R  / PF1.15 / DD4.8R
2026-04: 37 trades / +1.8R  / PF1.12 / DD3.0R
2026-05: 16 trades / +8.0R  / PF3.00 / DD2.0R
```

All reviewed months are positive. March and April are weak but not negative.

## Important generated files

Fixed preset:

```text
config/mochipoyo/gold_mochipoyo_rr12_refined_fixed_filters.json
```

Fixed-preset final portfolio:

```text
data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_final_portfolio.csv
```

Fixed-preset month summary:

```text
data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_by_month.csv
```

Fixed-preset filter coverage:

```text
data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_filter_coverage.csv
```

Fixed-preset summary:

```text
data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_summary.json
```

## Known strengths

- Strong improvement versus the broad candidate set.
- All reviewed months are positive.
- Low final max DD: `4.8R`.
- Max consecutive losses: `4`.
- Does not rely on a single timeframe pair.
- BUY and SELL both contribute, although SELL contributes more trades.
- Filter reasons are consistent with the guide: Granville, EMA-band pullback/retrace, RCI zones/turns, MACD divergence/hidden divergence.
- Fixed-filter preset removes leaderboard re-ranking instability.

## Known weaknesses

- M1/M5 outcome window is short and starts around `2025-11-28`.
- March and April are weak months.
- The refined filters were selected using the same available window, so overfitting risk remains.
- Row count can change when raw MT5 CSVs are updated.
- This must not be mixed with BTC.
- BTC requires separate spread-included net validation.

## Required next checks

Before this can move toward notification or AI review:

1. Manually inspect a sample of winning and losing rows.
2. Add an explicit timing-audit report for the final fixed-preset trades.
3. Confirm that fixed-preset final rows are stable for a frozen input CSV snapshot.
4. Keep BTC separate and perform BTC net spread-included validation independently.

## Decision

```text
GOLD_MOCHIPOYO_RR12_REFINED = provisional leading GOLD candidate
```

Not allowed yet:

```text
live notification
AI review automation
portfolio combination with BTC
```

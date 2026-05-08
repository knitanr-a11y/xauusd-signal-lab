# GOLD H1/H4 Bear A/B dry-run validation notes

Last updated: 2026-05-08

## Scope

This document records the current isolated dry-run validation status for the SELL-only strategy family:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

This strategy is still separated from:

- Mochipoyo live/demo/autotrade flow
- Existing `run_mochipoyo_gold_demo_autotrade_forever_aligned.bat`
- GOLD C_ENV BUY strategy
- Multi-strategy router
- Real MT5 order placement

## Current strategy ranks

```text
CORE_AB_CONFIRM = A and B
  trade_enabled = true
  lot_multiplier = 2.0

B_ONLY_SAFE = B and not A
  trade_enabled = true
  lot_multiplier = 1.0

A_ONLY_OBSERVE = A and not B
  trade_enabled = false
  lot_multiplier = 0.0
```

## Current A condition summary

A is the stricter confirmation side.

```text
H1:
  close < EMA20
  EMA20 < EMA50
  EMA20 slope3 < 0
  (EMA20 - close) / ATR14 <= 1.60

H4:
  close < EMA20
  EMA20 < EMA50

D1:
  close < EMA20

M15:
  low < previous rolling low 16
  close_pos <= 0.45
  MACD hist delta < 0
  range / ATR14 >= 0.90
```

## Current B condition summary

B is intentionally broader than A.

```text
H1:
  close < EMA50
  EMA20 < EMA50
  (EMA20 - close) / ATR14 <= 1.60

H4:
  EMA20 < EMA50

D1:
  close < EMA20

M15:
  low < previous rolling low 6
  close_pos <= 0.50
  MACD hist < 0
  MACD hist delta < 0
```

## B_ONLY_SAFE H1 strict filter decision

A stricter variant was tested where B also required:

```text
H1 close < H1 EMA20
```

Comparison script:

```text
scripts/compare_gold_h1h4_bear_ab_bonly_h1_strict.py
```

Output directory:

```text
data/research_results/gold_h1h4_bear_ab_bonly_h1_strict_compare
```

Result summary:

```text
current_b:
  trades: 68
  win_rate: 55.88%
  total_r: +46.0R
  lot_weighted_r: +63.0R
  PF: 2.53
  max_dd_r: 5.0R

strict_b_h1_close_below_ema20:
  trades: 55
  win_rate: 47.27%
  total_r: +23.0R
  lot_weighted_r: +41.0R
  PF: 1.79
  max_dd_r: 7.0R
```

B_ONLY_SAFE rank comparison:

```text
current_b / B_ONLY_SAFE:
  trades: 46
  win_rate: 54.35%
  total_r: +29.0R
  PF: 2.38
  max_dd_r: 5.0R

strict_b_h1_close_below_ema20 / B_ONLY_SAFE:
  trades: 34
  win_rate: 38.24%
  total_r: +5.0R
  PF: 1.24
  max_dd_r: 6.0R
```

Trades removed by the strict H1 filter were profitable as a group:

```text
removed_by_strict_filter:
  trades: 23
  wins: 14
  losses: 9
  win_rate: 60.87%
  total_r: +19.0R
  PF: 3.11
  max_dd_r: 3.0R
```

Decision:

```text
Do not add H1 close < H1 EMA20 to B_ONLY_SAFE.
Keep the current B_ONLY_SAFE H1 condition.
```

Reason:

The strict filter removed many profitable pullback/re-breakdown cases. B_ONLY_SAFE appears to benefit from allowing H1 close to recover above EMA20 while H1 remains below EMA50, H4 remains bearish, D1 remains bearish, and M15 breaks down with negative MACD momentum.

## Entry mode note

Historical replay now supports two entry modes:

```text
--entry-mode live_close
--entry-mode next_m15_open
```

`live_close`:

```text
entry_time = signal M15 close_time
entry_price = signal M15 close
```

`next_m15_open`:

```text
entry_time = signal M15 close_time
entry_price = next M15 bar open
```

Validation case:

```text
as_of_m15_close_time = 2026-02-03 04:30:00
```

Observed values:

```text
live_close:
  entry_price_reference = 4773.20
  SL = 4783.20
  TP = 4753.20

next_m15_open:
  entry_price_reference = 4773.17
  SL = 4783.17
  TP = 4753.17
```

Both modes completed M1 position monitoring successfully.

## Historical replay script guidance

Preferred replay script:

```text
scripts/run_gold_h1h4_bear_ab_historical_replay_simple.py
```

Reason:

The older historical cycle script attempted to save long command-log paths under the MT5 data directory and hit Windows path-length/file-path issues. The simple replay script avoids those long command-log paths and has passed the positive path checks.

Older script to avoid for now:

```text
scripts/run_gold_h1h4_bear_ab_historical_dry_run_cycle.py
```

It should be treated as legacy/debug-only unless cleaned up later.

## Confirmed dry-run paths

Validated so far:

```text
no-signal path: PASS
CORE_AB_CONFIRM signal-created path: PASS
CORE_AB_CONFIRM lot x2.0 path: PASS
CORE_AB_CONFIRM M1 TP path: PASS
B_ONLY_SAFE signal-created path: PASS
B_ONLY_SAFE lot x1.0 path: PASS
B_ONLY_SAFE M1 TP path: PASS
B_ONLY_SAFE M1 SL path: PASS
duplicate signal_key path: PASS
resolved position ledger path: PASS
resolved signal skip path: PASS
duplicate order intent safety path: PASS
entry_mode live_close path: PASS
entry_mode next_m15_open path: PASS
```

## Resolved-position handling

Position monitor now writes terminal results to:

```text
position_result_ledger.csv
```

Terminal statuses:

```text
TP_TOUCHED_DRY_RUN
SL_TOUCHED_DRY_RUN
TIME_EXIT_CLOSE_INTENT_REQUIRED
TIME_EXIT_ALREADY_LOGGED
```

If a `signal_key` already exists in `position_result_ledger.csv`, later monitor runs skip it by default.

## Duplicate order intent handling

Duplicate signals now write:

```text
intent_type = DUPLICATE_SKIP
action = NO_OPEN_POSITION_INTENT
trade_enabled = false
lot.effective_lot = 0.0
```

This prevents a duplicate signal from leaving an `OPEN_POSITION`-like order intent file behind.

## Remaining validation items

Next items:

```text
TIME_EXIT path validation
15-minute continuous dry-run loop validation
BUY/SELL router integration preparation
Existing Mochipoyo/demo/autotrade integration planning
```

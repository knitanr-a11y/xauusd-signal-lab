# GOLD V2 25C82 Field formula implementation audit result

Created UTC: 2026-06-08T07:58:07.314959+00:00

Status: `FIELD_FORMULA_IMPLEMENTED_AUDIT_ONLY_RAW_CONDITION_REPLAY_PASSED_VALUE_PARITY_STILL_UNPROVEN`

## Scope

This is an audit-only OHLC formula implementation and raw-condition replay check. It does not approve source recovery, live evaluator, final signal, Discord, MT5, or AI use.

## What was implemented

The 38 required raw/CoreB features identified in 25C81 were implemented from the uploaded OHLC candles.

Feature families implemented:

- ATR-normalized returns: `ret_*_atr`, `abs_ret_*_atr`
- ATR-normalized ranges: `range_*_atr`
- Donchian positions: `donch_pos_*`
- ATR-normalized distance to high/low: `dist_high_*_atr`, `dist_low_*_atr`
- range compression ratios: `compression_range_*_*`
- EMA slope normalized by ATR: `ema*_slope_*_atr`
- M5 equivalents for the raw filters: `m5_*`
- candle upper wick normalized by ATR: `upper_wick_atr`

## Convention test

The following conventions were compared:

| M15 convention | M5 convention | all-condition pass ratio |
| --- | --- | ---: |
| exclusive / previous bar | exclusive / previous bar | 0.651259 |
| exclusive / previous bar | inclusive / current bar | 0.692444 |
| inclusive / current bar | exclusive / previous bar | 0.947733 |
| inclusive / current bar | inclusive / current bar | 1.000000 |

Best convention:

```text
M15: inclusive/current-bar
M5: inclusive/current-bar
```

## Main result

Using inclusive M15 + inclusive M5 OHLC feature calculations:

```text
raw rows evaluated: 16875
base_condition pass rows: 16875
added_filter_text pass rows: 16875
all-condition pass rows: 16875
all-condition pass ratio: 1.000000
```

This means every row in `rr125_raw_signal_ledger.csv` satisfies its stored `base_condition` and `added_filter_text` when the 25C82 OHLC feature formulas are applied.

## Interpretation

This is a strong reproduction result, but it must be interpreted correctly.

What is now proven:

- The 38 required feature formulas are implementable from OHLC.
- The raw RR125 condition text can be replayed at threshold level.
- The correct convention for raw condition replay appears to be inclusive/current-bar for both M15 and M5.

What is not yet proven:

- Exact numeric feature-value parity against the original source snapshot, because the raw ledger stores condition text and thresholds but not the original feature values.
- A002 772 result use, because 25C79 still has 716 ambiguous A002-to-raw bindings.
- CoreA/CoreB/MEDIUM full membership replay.
- Live/final evaluator parity.

## Relationship to 25C80

25C80 showed the raw outcome engine was almost exactly reproducible from M1 candles:

```text
16871 / 16875 profit_r + exit_time rows matched
WR matched exactly
PF delta about -0.000539
```

25C82 now adds that the raw condition text also replays perfectly under inclusive M15/M5 formulas.

Together:

| Layer | Status |
| --- | --- |
| raw condition threshold replay | PASSED |
| raw outcome replay | NEAR_EXACT |
| A002 exact raw binding | BLOCKED |
| CoreA/CoreB/MEDIUM OHLC membership replay | NOT_READY |
| live/final signal | OFF |

## Remaining blockers

| blocker_id | component | status | needed |
| --- | --- | --- | --- |
| 25C82-B001 | A002_RESULT_BINDING | BLOCKED | exact A002-to-raw row identity key or source row index |
| 25C82-B002 | SOURCE_FEATURE_VALUE_PARITY | NOT_PROVEN | original source feature snapshots if value-level parity is required |
| 25C82-B003 | RAW_UNIVERSE_REPLAY | NEXT | replay all 33 raw rules over OHLC feature universe and compare source row counts / clusters |
| 25C82-B004 | COREB_CLUSTER_REPLAY | BLOCKED_NEXT | same_count / unique_origins cluster reconstruction still required |
| 25C82-B005 | LIVE_FINAL_SIGNAL | OFF | no external actions until all parity gates pass |

## Next recommended step

`25C83_RAW_RULE_REPLAY_AND_CLUSTER_RECONCILIATION_AUDIT_ONLY`

Goal:

- apply the 33 raw RR125 rule texts over the OHLC-derived feature universe;
- compare generated raw candidates against `rr125_raw_signal_ledger.csv` counts;
- compare cluster/top-ledger rows against `rr125_top_ledgers.csv`;
- keep A002 result binding blocked unless exact row identity becomes available.

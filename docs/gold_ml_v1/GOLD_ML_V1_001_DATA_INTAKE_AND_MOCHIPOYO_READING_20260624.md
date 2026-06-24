# GOLD ML V1 — Phase001 Data Intake and Mochipoyo Reading Record

Date: 2026-06-24  
Status: `GOLD_ML_V1_001_DATA_SOURCE_AUTHORIZED_INTAKE_IN_PROGRESS`  
Decision: `USE_AUTHORIZED_RAW_HISTORY_AS_PRIMARY_AND_LIVE_FILES_AS_EXTENSION`

## 1. Authorized raw candle sources

The user explicitly authorized these existing raw market-data sources for the clean rebuild:

Historical primary source, relative to the active MT5 `MQL5\Files` directory:

`gold_v3_2023_2026\`

Live extension source:

`MQL5\Files\goldsharp_*.csv`

The historical folder name does not authorize any old GOLD V3 code, model, feature, label, threshold, candidate, metric, or derived output. Only the raw OHLCV CSV files listed in `config/gold_ml_v1/data_source_authorization_20260624.json` are allowed.

## 2. Exact timestamp contract

The CSV `time` column is the bar-open timestamp.

The latest row in every file is already a closed bar and must be retained.

For each timeframe:

`bar_close_time = bar_open_time + timeframe_duration`

Therefore:

- M1 open 18:14 becomes available at 18:15;
- M5 open 18:10 becomes available at 18:15;
- M15 open 18:00 becomes available at 18:15;
- H1 open 17:00 becomes available at 18:00;
- H4 open 12:00 becomes available at 16:00;
- D1 open 2026-06-22 00:00 becomes available at 2026-06-23 00:00.

No program may discard the latest row by assuming it is open.

No feature, signal, label input, or as-of join may make a bar available at its open timestamp. Higher-timeframe joins must satisfy:

`higher_timeframe_bar_close_time <= decision_time`

Raw MT5 server timestamps are preserved without JST conversion.

## 3. Uploaded CSV audit

All 12 uploaded CSV files have the exact schema:

`time,open,high,low,close,tick_volume,spread,real_volume`

Across all files:

- duplicate timestamps: 0;
- out-of-order rows: 0;
- invalid OHLC rows: 0;
- timeframe alignment violations: 0.

Historical primary row counts and observed uploaded ranges:

| Timeframe | Rows | First open | Last open | Last close under contract |
|---|---:|---|---|---|
| M1 | 1,225,431 | 2023-01-03 01:00 | 2026-06-19 19:54 | 2026-06-19 19:55 |
| M5 | 245,327 | 2023-01-03 01:00 | 2026-06-19 19:50 | 2026-06-19 19:55 |
| M15 | 81,781 | 2023-01-03 01:00 | 2026-06-19 19:45 | 2026-06-19 20:00 |
| H1 | 20,459 | 2023-01-03 01:00 | 2026-06-19 19:00 | 2026-06-19 20:00 |
| H4 | 5,352 | 2023-01-03 00:00 | 2026-06-19 16:00 | 2026-06-19 20:00 |
| D1 | 894 | 2023-01-03 00:00 | 2026-06-19 00:00 | 2026-06-20 00:00 |

Live-extension row counts and observed uploaded ranges:

| Timeframe | Rows | First open | Last open | Last close under contract |
|---|---:|---|---|---|
| M1 | 150,259 | 2026-01-20 09:30 | 2026-06-23 18:14 | 2026-06-23 18:15 |
| M5 | 90,052 | 2025-03-14 06:30 | 2026-06-23 18:10 | 2026-06-23 18:15 |
| M15 | 30,018 | 2025-03-14 07:00 | 2026-06-23 18:00 | 2026-06-23 18:15 |
| H1 | 20,005 | 2023-02-01 14:00 | 2026-06-23 17:00 | 2026-06-23 18:00 |
| H4 | 10,001 | 2019-12-30 20:00 | 2026-06-23 12:00 | 2026-06-23 16:00 |
| D1 | 5,000 | 2007-03-30 00:00 | 2026-06-22 00:00 | 2026-06-23 00:00 |

The live files intentionally have different lookback depths. The historical six-file set remains the primary common-period source. Live files extend and refresh it.

## 4. Historical/live parity

Every overlapping uploaded row matched exactly across all seven numeric columns:

| Timeframe | Exact matching overlap rows | Mismatch rows |
|---|---:|---:|
| M1 | 147,845 | 0 |
| M5 | 89,569 | 0 |
| M15 | 29,857 | 0 |
| H1 | 19,965 | 0 |
| H4 | 5,352 | 0 |
| D1 | 894 | 0 |

Merge behavior is therefore frozen as:

1. use historical data as the base;
2. compare every overlap row exactly;
3. fail closed on any overlap mismatch;
4. append only live timestamps not already present;
5. retain the latest closed live row;
6. never silently prefer one conflicting source.

## 5. Cross-timeframe consistency

Historical M1 aggregation reproduced the supplied historical M5, M15, H1, H4, and D1 OHLC and tick-volume values exactly for every corresponding bar.

Observed non-contiguous timestamp gaps mainly follow the broker trading schedule, including daily maintenance breaks, weekends, holidays, and occasional sparse minute bars. Gaps must be classified and reported; they must not be blindly filled with fabricated candles.

## 6. Deep reading of the Mochipoyo guide

The guide is a discretionary confluence method rather than a complete deterministic algorithm.

The central interpretation is:

1. Treat the chart as waves, not isolated candles.
2. Establish higher-timeframe context before taking a lower-timeframe entry.
3. Prefer clear trends and sufficiently high volatility; avoid low-volatility congestion and messy ranges.
4. Combine multiple reasons rather than entering because one alert appeared.
5. Use lower-timeframe trend continuation in the direction supported by the higher timeframe.
6. Treat divergence as a possible reversal clue and hidden divergence as a possible trend-continuation clue.
7. Use EMA 20/30/40 ordering and slope/congestion as direction and trend-quality evidence.
8. Use RCI location and movement, especially near plus/minus 70 or prior RCI turning zones.
9. Include roll reversal, prior highs/lows, support/resistance, and round numbers as context.
10. Place stops near recent structural highs/lows and seek naturally available reward of at least approximately 1:1.
11. Consider exiting when short or medium RCI reaches the opposite side, at a prior price extreme, or at a separate exit indication.
12. Accept low trade frequency; only strong confluence should become a candidate.

The guide recommends these main/higher-timeframe relationships:

- M1 with H1;
- M5 with H4;
- M15 with H4;
- H1 with D1;
- for longer swing research, H4 with W1 and D1 with W1 or MN1.

This structure fits the GOLD_ML_V1 objective: each relationship and setup family should become a separate candidate family, not be merged into one changing main candidate.

## 7. Initial independent candidate-family interpretation

No candidate is registered yet. The following are research families only:

- higher-timeframe trend continuation plus lower-timeframe pullback entry;
- higher-timeframe RCI reversal plus lower-timeframe trend formation;
- hidden-divergence continuation;
- regular-divergence reversal;
- EMA-ordered trend pullback;
- roll-reversal retest;
- high-volatility trend continuation;
- round-number-supported setup;
- combinations of the above, each with a separate immutable candidate ID if later registered.

LONG and SHORT must be evaluated separately. A rule change, direction change, timeframe-pair change, label change, or exit change requires a new candidate ID.

## 8. Unresolved items before feature and label contracts are frozen

The guide does not provide enough information to freeze these values without user confirmation:

1. exact RCI periods for short, medium, and long lines;
2. exact MACD fast, slow, and signal periods;
3. exact Mochipoyo alert formula or whether the new ML system should learn setups without reproducing the original alert;
4. exact ZigZag settings, if ZigZag is to be a deterministic feature;
5. initial label/exit design: fixed TP/SL/horizon, structural swing exit, RCI-opposite-side exit, or separate label families;
6. exact MT5 broker symbol name and point size used to convert the raw `spread` integer to price cost.

These items must not be guessed or inherited from the old GOLD project.

## 9. Current boundary

Completed:

- source authorization recorded;
- uploaded raw-file structural audit completed;
- open-time/close-time semantics fixed;
- historical/live merge parity confirmed;
- Mochipoyo guide interpreted into independent research families.

Not yet completed:

- Phase001 final dataset split contract;
- feature contract;
- label contract;
- model training;
- candidate registration;
- portfolio research.

No training or candidate promotion is authorized yet.

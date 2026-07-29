# BTC FF04 bar-time semantics and causal rebuild preregistration

- repository: `knitanr-a11y/xauusd-signal-lab`
- working branch: `feature/btc-fresh-forward-research`
- stage: `BTC_FF04_BAR_TIME_SEMANTICS_AND_CAUSAL_REBUILD_PREREGISTRATION`
- candidate family: `BTC7N_CAUSAL_M15_TREND_IMPULSE_REBUILD_V1`

## Why FF04 exists

BTC7R passed direct prefix causality but failed selection-provenance trust. Before any replacement search, FF04 removes a recurring ambiguity: MT5 candle CSV `time` is the bar OPEN timestamp, not the close timestamp.

A close-derived value must never be considered known at `time` itself.

## Mandatory bar clock

| Timeframe | CSV `time` means | Earliest usable time |
|---|---|---|
| M5 | M5 bar open | `time + 5 minutes` |
| M15 | M15 bar open | `time + 15 minutes` |
| H1 | H1 bar open | `time + 60 minutes` |
| H4 | H4 bar open | `time + 4 hours` |
| D1 | D1 bar open | `time + 24 hours` |

Raw candidate logic remains in naive MT5 broker-server wall-clock time. UTC conversion is used only after candidate construction for period boundaries and reporting.

## Current BTC7R implementation check

The current base engine explicitly creates:

- `h1_decision_time = h1.time + 1 hour`
- `entry_time = m15.time + 15 minutes`
- entry from the exact M5 row whose open timestamp equals `entry_time`
- exit observation time as `m5.time + 5 minutes`

Therefore the current engine does not treat the M15 close as known at the M15 open timestamp.

FF04 nevertheless rechecks this dynamically and statically because future rebuild code must not rely on memory or comments.

## Conservative rebuild rule

The replacement search is stricter than merely using `source_available_time <= M15 close`.

For the H1 trend state of an M15 signal bar, only H1 rows satisfying:

`H1 available_time <= signal M15 open time`

may be used.

This deliberately excludes an H1 bar that closes at the same instant as the M15 signal bar closes. It prevents same-boundary processing-order ambiguity.

The M15 signal bar itself becomes available at:

`decision_time = M15 open time + 15 minutes`

Entry requires:

`M5 time == decision_time`

A nearest row, later row, interpolation or future fallback is forbidden. Missing exact M5 entry means `NO_TRADE`.

## FF04 actual-data audit

FF04 reads the already reviewed FF01 paths and requires the reviewed FF03 status. For M5/M15/H1/H4/D1 it checks:

- required OHLC columns;
- valid, ascending, unique timestamps;
- expected short-gap cadence;
- `available_time = time + duration`;
- latest row is already closed under open-time semantics;
- recent continuous M15 closes have an exact M5 open at the same boundary;
- static current-engine time expressions;
- synthetic M5/M15/H1 causality sentinels;
- no nearest-future entry fallback.

Source files are hashed before and after stable snapshot creation. Internal snapshots are deleted and are not included in the ZIP.

The MT5 exporter source itself is not treated as proven by this sparse FF04 scope. That evidence gap never permits interpreting `time` as close time. The downstream contract always treats it as open time and fails closed.

## Search preregistration

FF04 freezes the complete replacement grammar before any candidate performance run:

- trend separation: `0.25 / 0.50 / 0.75 ATR`
- M15 impulse: `1.75 / 2.25 / 2.75 ATR`
- directional close location: `0.80 / 0.90`
- trend-age windows: `0-48 / 24-96 / 48-168 hours`
- target: `1.0R / 1.5R`

Total: `108` cells.

Fixed items include EMA50/EMA200 H1 trend, EMA20 M15 side, ATR14, 0.1 ATR stop buffer, 100-pip risk cap, 50-pip minimum reward, $30 spread, $10 per strategy pip, one open position per cell and same-M5 SL priority.

## Outcome isolation

All data after:

`2026-07-02 02:15:00 UTC`

are excluded from design, ranking and diagnostics. The six FF02 losses cannot be used to add a filter, remove LONG, remove a time window or alter thresholds.

All earlier results are retrospective research only. They cannot by themselves authorize promotion.

## Evaluation preregistration

The later search stage must:

- report all 108 cells;
- use the six frozen stitched OOS segments;
- use a 5,000-resample calendar-week block bootstrap;
- apply max-statistic familywise adjustment across all 108 cells;
- preserve rejected cells and exact trial counts;
- apply all survivor gates without relaxation;
- return `NO_CANDIDATE` when no cell passes;
- select at most one cell by the frozen deterministic sort order;
- disallow manual override.

The selected rule, when one exists, must be committed before a new prospective boundary begins. The prospective boundary is the selected-rule freeze commit time, not the old July 2 boundary.

## FF04 outputs

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\04_bar_time_semantics_rebuild_foundation\LATEST\`

- `00_READ_ME_FIRST.txt`
- `01_time_semantics_summary.json`
- `02_time_semantics_report.txt`
- `03_timeframe_manifest.csv`
- `04_causal_sentinel_tests.csv`
- `05_rebuild_preregistration.json`
- `06_current_engine_contract.json`
- `99_UPLOAD_PACKAGE.zip`

## Safety and stop

FF04 does not run candidate performance, search 108 cells, select a rule, alter BTC7R, design lots, enable live use, send Discord messages, send MT5 orders or touch GOLD/MOCHIPOYO.

Stop after uploading the FF04 ZIP. The actual search stage is not automatically authorized.

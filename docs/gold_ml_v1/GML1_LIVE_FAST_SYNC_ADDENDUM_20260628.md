# GML1 live fast-sync addendum

Date: 2026-06-28

## Why this change was required

The first BAT-loop version executed the full pandas runtime every 60 seconds, even when all MT5 CSV files were unchanged. A Sunday log sample showed 30 consecutive runs taking 3.81 to 4.12 seconds each, with an average of 3.895 seconds, despite no candle updates.

The candidate rules are not simplified in this change. The optimization changes only input polling, M1 read range and cross-timeframe readiness.

## New polling model

The BAT loop now polls every two seconds with `probe_live_inputs.py`, which uses only Python's standard library and file metadata.

- If all six CSV signatures match `live_state.json:input_signatures`, pandas is not started.
- The heavy runtime starts only when one or more CSV files change.
- An idle heartbeat is printed every 30 unchanged polls by default.
- `GML1_LIVE_INTERVAL_SECONDS` can override the two-second poll.
- `GML1_LIVE_IDLE_HEARTBEAT_TICKS` can override the idle heartbeat interval.

On weekends or any other period without candle updates, the loop remains in `IDLE_NO_CHANGE` behavior rather than recalculating all features repeatedly.

## Read optimization without rule changes

- M1 is read from the file tail only, beginning before the earliest required cursor or open position.
- The number of M1 tail rows expands automatically when the runtime has been stopped for a longer period.
- M5 is not a candidate input for the four enabled sleeves and only its latest rows are read for contract visibility.
- M15, H1, H4 and D1 retain full-history calculation so Wilder, EMA, percentile and state logic do not change.

No ATR, RSI, RCI, EMA, percentile, state-onset, one-position or TP/SL/TIME rule was approximated.

## Export-delay handling

There is no longer a fixed assumption that all timeframes will be written within three seconds.

The runtime retries until the required rows actually exist:

1. A new M15 or H1 row must appear in its own CSV.
2. The exact M1 bar whose open time equals the decision close time must exist.
3. If an actual M15 close exists at a four-hour boundary, the matching H4 close must exist before that boundary is processed.
4. If an actual H1 close exists at a daily boundary, the matching D1 close must exist before that boundary is processed.
5. If a file changes during probing or reading, the run is deferred and no cursor advances.

Weekend gaps are handled from actual source rows. A missing calendar boundary that has no M15/H1 close row does not create a false H4/D1 wait.

## State migration

Existing `live_state.json` files are compatible. On the first run after this update, the runtime adds:

- `input_signatures`
- `last_observed_times`
- `live_dir`

When the current source cursors have not advanced and no position requires M1 tracking, this migration completes through the lightweight tail-probe path without a full feature calculation.

## Expected status values

- `IDLE_NO_CHANGE`: no input file signature changed.
- `IDLE_NO_RELEVANT_BAR`: a file changed, but no new synchronized M15/H1 decision and no open position required processing.
- `WAITING_FOR_TIMEFRAME_SYNC`: a source row exists but its exact M1 entry row is not yet available.
- `DEFERRED`: one or more files changed during the same probe/read operation.
- `PASS`: synchronized source rows were processed successfully.

The controls remain audit-only. Discord, final signal and MT5 orders remain disabled.

# GOLD V3 Stage115D Spec — STALE_DATA_WATCHDOG

Created JST: `2026-06-14`

## Purpose

Stage115D adds a stale-data watchdog before true demo-live operation.

It separates:

```text
normal market idle
```

from:

```text
unexpected stale CSV during expected market time
```

## Why this stage is needed

Stage115C can run as a single BAT loop and can catch internal runtime errors.

However, market stops must not be treated as runtime errors. Weekends and broker rollover quiet periods are expected.

Stage115D writes a review queue item only when data is stale during an expected active period.

## Normal idle states

These are not errors:

```text
weekend
broker rollover quiet period
no new candle because market is closed
NO_SIGNAL
unchanged queue
```

## Watchdog states

```text
OK
MARKET_CLOSED_EXPECTED
ROLLOVER_QUIET_EXPECTED
WATCH_STALE
STOP_REVIEW_STALE
INPUT_MISSING
INPUT_PARSE_ERROR
```

## Default schedule assumptions

Timezone: JST.

Expected closed-market windows:

```text
Saturday all day JST
Sunday before 08:00 JST
Monday before 07:00 JST conservative startup quiet
Daily rollover quiet: 06:55-07:10 JST
```

These are conservative because broker/server schedules may vary.

## CSV inputs

The watchdog checks likely live OHLC CSV paths under the MT5 Files directory:

```text
candles_history_M15.csv
candles_history_M5.csv
candles_history_H1.csv
```

M15 is the primary freshness check.

## Thresholds

Default:

```text
watch_stale_minutes: 45
stop_stale_minutes: 90
```

If M15 latest closed row is older than 45 minutes during expected active time, Stage115D creates WATCH_STALE.

If older than 90 minutes, Stage115D creates STOP_REVIEW_STALE.

## Queue behavior

Stage115D may write a queue item to:

```text
FX_OUTPUTS/gold_v3/115a/queue/YYYY-MM/gold_v3_115d_watchdog_YYYY-MM-DD.jsonl
```

The queue item is deduplicated by state key so it does not send every minute for the same stale condition.

## Outputs

```text
FX_OUTPUTS/gold_v3/115d/current/latest_watchdog_status.json
FX_OUTPUTS/gold_v3/115d/state/watchdog_state.json
FX_OUTPUTS/gold_v3/115d/journal/YYYY-MM/gold_v3_115d_watchdog_YYYY-MM-DD.jsonl
FX_OUTPUTS/gold_v3/115d/gold_v3_115d_summary.json
FX_OUTPUTS/gold_v3/115d/paste_me.txt
```

## Prohibited

Stage115D does not execute orders, mutate source CSVs, change the CSV contract, use open/as-of candles, remove candidates, or reference quarantined systems.

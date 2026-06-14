# GOLD V3 Stage115C Spec — SINGLE_BAT_LOOP

Created JST: `2026-06-14`

## Purpose

Stage115C integrates 115A and 115B into one BAT-driven loop.

The user requested:

```text
- one BAT, not two
- if the BAT/runtime stops because of an error, notify Discord
- every minute at second 05
- folder layout remains tidy
- win/loss history remains easy to trace
- old notification history may be pruned after about one month
- consider weekends and MT5 date-rollover market stops
```

## Important market-stop handling

Market stop is not treated as an error.

Stage115C must treat these as normal idle states:

```text
- no latest signal file
- NO_SIGNAL input
- unchanged queue
- weekend / broker quiet time
- MT5 daily rollover quiet period
```

A runtime error is different from a market stop. Only runtime errors should trigger emergency notification.

## Components

Stage115C runs:

```text
115A queue/storage step
115B sender step
```

inside one loop.

## Timing

```text
target_second: 5
```

## Error notification

If an exception occurs inside the Python loop, Stage115C catches it, writes an error journal, and attempts to send one emergency notification using the local `.env` endpoint.

The endpoint value must not be printed.

## Prohibited

Still prohibited:

```text
MT5 order execution
real account execution
automatic position open/close
source CSV mutation
CSV contract mutation
open/as-of logic
candidate pool removal
```

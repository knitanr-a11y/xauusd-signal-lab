# GOLD V3 Stage237 Runtime Latest-State Detector Spec

Date: 2026-06-19  
Stage: `GOLD_V3_237_RUNTIME_LATEST_STATE_DETECTOR`  
Status: `DEMO_RUNTIME_DETECTOR / LATEST_STATE_UPDATER / NO_ORDER_DIRECT`

## Problem

Stage236/234/227/226/233 were running, but the source state read by Stage227 was stale:

```text
FX_OUTPUTS/gold_v3/217/staging_retention/latest_state.json
final_route=NO_SIGNAL
latest_closed_m15_dt=2026-06-16 16:45:00
```

Therefore Stage227 correctly produced an empty runtime queue, and Stage226/233 had nothing to process.

## Purpose

Stage237 reads the latest closed market CSV rows and updates:

```text
FX_OUTPUTS/gold_v3/217/staging_retention/latest_state.json
FX_OUTPUTS/gold_v3/217/staging_retention/trade_signal_ledger.csv
FX_OUTPUTS/gold_v3/217/staging_retention/no_signal_counters_daily_hourly.csv
```

This gives Stage227 a current source state to convert into a runtime queue.

## Inputs

Default MQL5 Files CSV paths:

```text
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
goldsharp_m5.csv
```

CSV latest row is contractually CLOSED. No open/as-of row is used.

## Detection version

Stage237 is a deterministic runtime technical detector bridge.

It uses:

```text
EMA20/30/40 trend alignment
MACD 6/13/4 histogram
RCI 9/14/18
H1/H4/D1 as-of context
M15 latest closed candle only
```

This is not a hidden ML model call. It is the first live bridge to stop stale latest_state behavior while preserving safety gates.

## Output behavior

If signal conditions pass:

```text
final_route=SECONDARY_AUDIT_CANDIDATE
strategy_role=SCALP_SECONDARY_CANDIDATE
candidate_id=RUNTIME_SCALP_TREND_PULLBACK_LONG or SHORT
signal_id populated
TP=15
SL=5
horizon_m5_bars=64
```

If conditions do not pass:

```text
final_route=NO_SIGNAL
latest_closed_m15_dt updated to the latest M15 row
signal_id empty
```

## Safety

Stage237 does not:

```text
- call Discord webhook
- call mt5.order_send
- place/close/modify orders
- enable final live
- enable payload activation
- import actual execution
- use theoretical outcome as input
- bypass F002
- remove candidate pool
```

## Next stage

Stage238 should run:

```text
Stage237 latest_state update
Stage234 coordinator
```

This preserves the existing Stage227/226/233 flow while adding the missing detector step.

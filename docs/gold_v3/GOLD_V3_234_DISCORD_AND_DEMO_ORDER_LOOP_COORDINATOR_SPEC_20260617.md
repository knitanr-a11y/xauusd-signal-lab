# GOLD V3 Stage234 Discord + Demo Order Loop Coordinator Spec

Date: 2026-06-17  
Stage: `GOLD_V3_234_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR`  
Status: `DEMO_ONLY / DISCORD_ALERT + DEMO_ORDER_COORDINATOR / BOUNDED_LOOP`

## Purpose

Stage234 coordinates the already-approved components:

```text
Stage227: runtime queue refresh
Stage226: demo Discord alert-only send loop
Stage233: MT5 DEMO order loop for SCALP/DAYTRADE 0.01 lot
```

Stage234 does not implement new signal logic. It calls the existing stages in order and records whether the queue, alert, and demo order paths stayed aligned.

## Basis

Stage233 passed:

```text
status=READY
runtime_queue_exists=True
cycle_count=60
order_send_call_count=0
order_placed_count=0
blocker_count=0
```

The latest queue was empty, so no order was sent.

## Stage234 cycle order

Each bounded cycle performs:

```text
1. Check Stage234 kill switch.
2. Wait until minute boundary + 5 seconds if requested.
3. Run Stage227 queue refresh.
4. Run Stage226 once against runtime/alert_only_queue.csv.
5. Run Stage233 one cycle against the same runtime queue.
6. Record return codes and paste/ledger paths.
```

## Scope

Stage234 may:

```text
- call Stage227, Stage226, Stage233 as subprocesses
- read runtime queue snapshots and local output files
- write coordinator ledger and summary
```

Stage234 must not directly:

```text
- call a Discord webhook itself
- call mt5.order_send itself
- place orders outside Stage233
- close or modify positions
- bypass Stage226/233 ledgers
- trade on NO_SIGNAL
- enable final live
- activate payload trading
- run an unbounded loop
```

## Safety gates inherited

Stage226 handles Discord duplicate suppression and NO_SIGNAL notification suppression.  
Stage233 handles DEMO account gate, GOLD# only, 0.01 lot, IOC, TP/SL required, signal_id dedupe, SCALP max 1, DAYTRADE max 1, total max 2, and NO_SIGNAL order suppression.

## Kill switch

Stage234 must stop if this file exists:

```text
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE234.txt
```

Stage233 also has its own kill switch:

```text
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE233.txt
```

## Output files

```text
FX_OUTPUTS/gold_v3/234/discord_and_demo_order_loop_coordinator/stage234_cycle_ledger.csv
FX_OUTPUTS/gold_v3/234/discord_and_demo_order_loop_coordinator/stage234_summary.json
FX_OUTPUTS/gold_v3/234/paste_me.txt
```

## Expected decision

```text
STAGE234_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR_READY
```

or blocked:

```text
STAGE234_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR_BLOCKED
```

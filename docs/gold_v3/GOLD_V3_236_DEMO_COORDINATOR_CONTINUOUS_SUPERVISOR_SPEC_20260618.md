# GOLD V3 Stage236 Demo Coordinator Continuous Supervisor Spec

Date: 2026-06-18  
Stage: `GOLD_V3_236_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR`  
Status: `DEMO_ONLY / CONTINUOUS_TIME_SUPERVISOR / NO_FINAL_LIVE`

## Purpose

Stage236 provides a continuous time runner for the existing Stage234 coordinator.

Stage235 proved the 24H bounded supervisor could run Stage234 repeatedly. The user then requested a no-time-limit version after Stage235 was stopped by kill switch.

Stage236 is continuous in time, but it is not risk-unbounded:

```text
- Stage236 itself never calls Discord webhook directly
- Stage236 itself never calls mt5.order_send directly
- Stage236 calls Stage234 once per minute
- Stage234 calls Stage227, Stage226, Stage233
- Stage233 keeps the DEMO-only, GOLD#, 0.01 lot, TP/SL, IOC, signal_id dedupe and position-cap gates
```

## Basis

Stage235 stopped by kill switch after successful repeated operation:

```text
cycle_count_completed=735
stage234_success_count=735
failed_stage234_count=0
runtime_queue_rows_last=0
kill_switch_present=True
stage234_kill_switch_present=True
```

The BLOCKED status was caused by kill switch validation, not a subprocess failure.

## Scope

Stage236 may:

```text
- call Stage234 as a subprocess once per minute
- wait until minute boundary + 5 seconds
- run continuously until kill switch, Ctrl+C, or subprocess failure
- write a cycle ledger
- update summary_json and paste_me after every cycle
```

Stage236 must not directly:

```text
- call a Discord webhook
- call mt5.order_send
- place an order
- close or modify positions
- bypass Stage226/233 ledgers
- trade on NO_SIGNAL
- enable final live
- activate payload trading
```

## Continuous-time policy

```text
cycle_count_default=0  # 0 means continuous
cycle_interval=minute boundary + 5 seconds
stage234_cycles_per_call=1
stop_on_stage234_failure=True
stop_on_kill_switch=True
```

## Risk gates remain inherited

Stage233 still enforces:

```text
- DEMO account only
- GOLD# only
- SCALP 0.01 lot
- DAYTRADE 0.01 lot
- ORDER_FILLING_IOC
- TP/SL required
- each signal_id once only
- SCALP max 1 position
- DAYTRADE max 1 position
- total max 2 Stage233 positions
- NO_SIGNAL no order
```

## Kill switches

Stage236 must stop if this file exists:

```text
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE236.txt
```

Stage235/234/233 kill switches may also stop it:

```text
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE235.txt
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE234.txt
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE233.txt
```

## Output files

```text
FX_OUTPUTS/gold_v3/236/demo_coordinator_continuous_supervisor/stage236_cycle_ledger.csv
FX_OUTPUTS/gold_v3/236/demo_coordinator_continuous_supervisor/stage236_summary.json
FX_OUTPUTS/gold_v3/236/paste_me.txt
```

## Expected decision

While running or stopped safely:

```text
STAGE236_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR_READY
```

If a subprocess or safety validation fails:

```text
STAGE236_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR_BLOCKED
```

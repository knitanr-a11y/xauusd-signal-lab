# GOLD V3 Stage235 Demo Coordinator Supervised 24H Runner Spec

Date: 2026-06-17  
Stage: `GOLD_V3_235_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER`  
Status: `DEMO_ONLY / 24H_BOUNDED_SUPERVISOR / NO_FINAL_LIVE`

## Purpose

Stage235 provides a 24-hour supervised runner for the existing Stage234 coordinator.

Stage234 already coordinates:

```text
Stage227: runtime queue refresh
Stage226: Discord alert-only once
Stage233: MT5 DEMO order loop one cycle
```

Stage235 calls Stage234 once per minute for up to 1440 cycles. Stage235 itself does not directly call Discord webhook or MT5 order APIs.

## Basis

Stage234 passed the 60-cycle coordinator test:

```text
status=READY
cycle_count_completed=60
stage227_success_count=60
stage226_success_count=60
stage233_success_count=60
failed_subprocess_count=0
runtime_queue_rows_last=0
blocker_count=0
```

## Scope

Stage235 may:

```text
- call Stage234 as a subprocess
- wait until minute boundary + 5 seconds
- run for a bounded maximum of 1440 cycles
- record per-cycle return codes
- stop on kill switch
- stop on subprocess failure
```

Stage235 must not directly:

```text
- call a Discord webhook
- call mt5.order_send
- place an order
- close or modify positions
- bypass Stage226/233 ledgers
- trade on NO_SIGNAL
- enable final live
- activate payload trading
- run unbounded autotrade
```

## Loop policy

```text
cycle_count_default=1440
cycle_interval=minute boundary + 5 seconds
stage234_cycles_per_call=1
hard_max_cycles=1440
```

This is 24-hour bounded operation, not unbounded live autotrade.

## Kill switch

Stage235 must stop if this file exists:

```text
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE235.txt
```

Stage234 and Stage233 kill switches remain effective:

```text
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE234.txt
FX_OUTPUTS/gold_v3/KILL_SWITCH_STAGE233.txt
```

## Output files

```text
FX_OUTPUTS/gold_v3/235/demo_coordinator_supervised_24h_runner/stage235_cycle_ledger.csv
FX_OUTPUTS/gold_v3/235/demo_coordinator_supervised_24h_runner/stage235_summary.json
FX_OUTPUTS/gold_v3/235/paste_me.txt
```

## Expected decision

```text
STAGE235_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER_READY
```

or blocked:

```text
STAGE235_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER_BLOCKED
```

# GOLD V3 Stage232 Demo Order Loop Dry-Run Audit Spec

Date: 2026-06-17  
Stage: `GOLD_V3_232_DEMO_ORDER_LOOP_DRY_RUN_AUDIT`  
Status: `DEMO_ONLY / LOOP_DRY_RUN / NO_ORDER_SEND`

## Purpose

Stage232 prepares the demo order loop without sending orders.

It reads the Stage227/228 runtime alert-only queue and records whether each queued SIGNAL would be eligible for a demo MT5 order.

## Basis

Stage231 passed reconciliation for the Stage230 demo order:

```text
stage230_order_placed=True
stage230_symbol=GOLD#
stage230_volume=0.01
positions_total_count=0
open_position_match_count=0
matched_history_order_count=2
matched_history_deal_count=2
blocker_count=0
```

## Scope

Stage232 may:

```text
- optionally run Stage227 queue refresh before reading the runtime queue
- read FX_OUTPUTS/gold_v3/runtime/alert_only_queue.csv
- confirm MT5 DEMO account
- inspect current GOLD# positions
- inspect Stage232 dry-run ledger for duplicate signal_id
- write dry-run planned order rows
- run once or loop in dry-run mode
```

Stage232 must not:

```text
- call mt5.order_send
- call mt5.order_check for actual sending
- place an order
- close or modify positions
- enable autotrade live mode
- enable final live
- activate payload trading
- trade on NO_SIGNAL
```

## Dry-run eligibility gates

For a queued row to become a planned dry-run order:

```text
- row must represent SIGNAL, not NO_SIGNAL
- signal_id must exist
- signal_id must not already exist in Stage232 planned ledger
- MT5 account must be DEMO
- symbol must be GOLD#
- volume must be exactly 0.01
- filling must be ORDER_FILLING_IOC
- TP/SL must be included by request design
- positions_get(symbol="GOLD#") must return no existing open position
```

If the runtime queue is empty, Stage232 may still PASS as `NO_SIGNAL_OR_EMPTY_QUEUE_DRY_RUN_READY`, provided all safety checks pass and no order_send occurs.

## Output files

```text
FX_OUTPUTS/gold_v3/232/demo_order_loop_dry_run/stage232_runtime_queue_snapshot.csv
FX_OUTPUTS/gold_v3/232/demo_order_loop_dry_run/stage232_planned_order_dry_run_ledger.csv
FX_OUTPUTS/gold_v3/232/demo_order_loop_dry_run/stage232_rejected_rows.csv
FX_OUTPUTS/gold_v3/232/demo_order_loop_dry_run/stage232_summary.json
FX_OUTPUTS/gold_v3/232/paste_me.txt
```

## Expected decision

```text
STAGE232_DEMO_ORDER_LOOP_DRY_RUN_READY
```

or blocked:

```text
STAGE232_DEMO_ORDER_LOOP_DRY_RUN_BLOCKED
```

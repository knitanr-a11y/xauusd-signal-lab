# GOLD V3 Stage231 MT5 Demo Order Reconciliation Audit Spec

Date: 2026-06-17  
Stage: `GOLD_V3_231_MT5_DEMO_ORDER_RECONCILIATION_AUDIT`  
Status: `DEMO_ONLY / READ_ONLY_RECONCILIATION / NO_NEW_ORDER / NO_CLOSE / NO_MODIFY`

## Purpose

Stage231 reconciles the single Stage230 demo order after the one-order send test.

Stage230 result basis:

```text
symbol=GOLD#
side=BUY
volume=0.01
filling=ORDER_FILLING_IOC
order_check_retcode=0
order_send_call_count=1
order_send_retcode=10009
order_send_comment=Request executed
order_ticket=958618622
deal_ticket=943656148
order_placed=True
```

## Scope

Stage231 may read:

```text
- Stage230 local summary JSON
- Stage230 order result JSON
- Stage230 order ledger CSV
- mt5.account_info()
- mt5.positions_get(symbol="GOLD#")
- mt5.history_orders_get(...)
- mt5.history_deals_get(...)
```

Stage231 must not:

```text
- create a new order
- close an order or position
- modify SL/TP
- enable autotrade
- enable final live
- activate payload trading
- use NO_SIGNAL to trade
```

## Required checks

```text
R231001 Stage230 summary exists
R231002 Stage230 order_placed=True
R231003 MT5 initializes
R231004 account is DEMO
R231005 Stage230 symbol is GOLD#
R231006 Stage230 volume is 0.01
R231007 Stage230 order/deal ticket recorded
R231008 positions_get executed
R231009 history_orders_get executed
R231010 history_deals_get executed
R231011 current open position or historical deal evidence exists
R231012 if open position exists, TP/SL fields are non-zero
R231013 no new order, no close, no modify
R231014 autotrade/final live/payload/NO_SIGNAL remain disabled
```

## Output files

```text
FX_OUTPUTS/gold_v3/231/mt5_demo_order_reconciliation/stage231_positions.json
FX_OUTPUTS/gold_v3/231/mt5_demo_order_reconciliation/stage231_history_orders.json
FX_OUTPUTS/gold_v3/231/mt5_demo_order_reconciliation/stage231_history_deals.json
FX_OUTPUTS/gold_v3/231/mt5_demo_order_reconciliation/stage231_reconciliation_summary.json
FX_OUTPUTS/gold_v3/231/paste_me.txt
```

## Expected decision

```text
STAGE231_MT5_DEMO_ORDER_RECONCILIATION_READY
```

or blocked:

```text
STAGE231_MT5_DEMO_ORDER_RECONCILIATION_BLOCKED
```

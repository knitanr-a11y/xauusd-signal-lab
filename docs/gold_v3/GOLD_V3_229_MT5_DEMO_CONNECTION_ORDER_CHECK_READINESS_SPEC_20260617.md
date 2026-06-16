# GOLD V3 Stage229 MT5 Demo Connection Order-Check Readiness Spec

Date: 2026-06-17  
Stage: `GOLD_V3_229_MT5_DEMO_CONNECTION_ORDER_CHECK_READINESS`  
Status: `DEMO_ONLY / CONNECTION_CHECK / ORDER_CHECK_ONLY / NO_ORDER_SEND / NO_AUTOTRADE`

## User request

The user requested moving toward MT5 demo-account connectivity. The user stated that demo-account execution is acceptable, but Stage229 remains limited to connection/readiness and order-check only.

## Scope

Stage229 may:

```text
- initialize MetaTrader5 Python connection
- read account_info and terminal_info
- confirm the account is demo by code
- inspect symbol information for XAUUSD or configured symbol
- inspect tick information
- build a demo-only order_check request
- call mt5.order_check only when demo account confirmation passes
- write local audit outputs under FX_OUTPUTS/gold_v3/229
```

Stage229 must not:

```text
- call mt5.order_send
- place an order
- modify/close positions
- enable final live
- enable autotrade
- activate payloads for trading
- notify NO_SIGNAL
- mutate source CSV, contracts, or production retention
```

## Demo account gate

The script must BLOCK unless the account can be identified as DEMO.

Primary check:

```text
account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
```

Fallback evidence may include server/name/company text containing demo, but real-account indicators must never be allowed.

## Symbol and volume policy

Default symbol:

```text
XAUUSD
```

Local override:

```text
GOLD_V3_MT5_SYMBOL=<symbol>
```

Default volume for readiness check:

```text
0.01
```

Local override:

```text
GOLD_V3_MT5_CHECK_VOLUME=0.01
```

The script must normalize volume against `volume_min`, `volume_max`, and `volume_step`.

## Order-check policy

Stage229 may call only:

```text
mt5.order_check(request)
```

Stage229 must not call:

```text
mt5.order_send(request)
```

The request is a readiness check only and does not place an order.

## Output files

```text
FX_OUTPUTS/gold_v3/229/mt5_demo_connection_order_check_readiness/mt5_account_info_redacted.json
FX_OUTPUTS/gold_v3/229/mt5_demo_connection_order_check_readiness/mt5_symbol_info.json
FX_OUTPUTS/gold_v3/229/mt5_demo_connection_order_check_readiness/mt5_order_check_result.json
FX_OUTPUTS/gold_v3/229/mt5_demo_connection_order_check_readiness/mt5_readiness_summary.json
FX_OUTPUTS/gold_v3/229/paste_me.txt
```

## Validation checks

```text
M229001 MetaTrader5 module imports
M229002 mt5.initialize succeeds
M229003 account_info exists
M229004 account is confirmed demo
M229005 terminal_info exists
M229006 symbol_select succeeds
M229007 symbol_info exists
M229008 tick info exists
M229009 volume normalized to symbol constraints
M229010 order_check executed only after demo gate
M229011 order_check returns a result object
M229012 mt5.order_send is not called
M229013 no final live, autotrade, payload activation, or source mutation
M229014 CSV latest row contract remains CLOSED and open/as-of is not introduced
```

## Expected decision

```text
STAGE229_MT5_DEMO_CONNECTION_ORDER_CHECK_READY
```

or blocked:

```text
STAGE229_MT5_DEMO_CONNECTION_ORDER_CHECK_BLOCKED
```

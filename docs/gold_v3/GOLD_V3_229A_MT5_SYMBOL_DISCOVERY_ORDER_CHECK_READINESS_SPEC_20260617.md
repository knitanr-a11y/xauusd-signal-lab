# GOLD V3 Stage229A MT5 Symbol Discovery Order-Check Readiness Spec

Date: 2026-06-17  
Stage: `GOLD_V3_229A_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_READINESS`  
Status: `DEMO_ONLY / SYMBOL_DISCOVERY / ORDER_CHECK_ONLY / NO_ORDER_SEND / NO_AUTOTRADE`

## Reason

Stage229 confirmed:

```text
mt5_module_imported=True
mt5_initialize_ok=True
account_info_exists=True
demo_account_confirmed=True
terminal_info_exists=True
```

but blocked because the fixed symbol `XAUUSD` was not selectable or visible for the broker account.

## Purpose

Stage229A searches available MT5 symbols and selects a likely gold symbol when `XAUUSD` is not directly usable.

## Symbol discovery order

1. Use `GOLD_V3_MT5_SYMBOL` if provided.
2. Try exact common names:

```text
XAUUSD
XAUUSD.
XAUUSDm
GOLD
GOLD.
Gold
```

3. Search `mt5.symbols_get()` for names containing:

```text
XAU
GOLD
```

4. Select the first symbol with valid tick and trade properties.

## Scope

Stage229A may:

```text
- initialize MetaTrader5 Python connection
- confirm DEMO account by code
- discover/select a gold-like symbol
- inspect symbol_info and tick info
- normalize 0.01 lot or configured volume
- call mt5.order_check only after DEMO confirmation
```

Stage229A must not:

```text
- call mt5.order_send
- place an order
- modify or close positions
- enable final live
- enable autotrade
- activate payloads
- notify NO_SIGNAL
```

## Expected decision

```text
STAGE229A_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_READY
```

or blocked:

```text
STAGE229A_MT5_SYMBOL_DISCOVERY_ORDER_CHECK_BLOCKED
```

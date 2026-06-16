# GOLD V3 Stage233 Demo Order Loop SCALP/DAYTRADE 0.01 Lot Spec

Date: 2026-06-17  
Stage: `GOLD_V3_233_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT`  
Status: `DEMO_ONLY / ORDER_LOOP / USER_APPROVED / NO_FINAL_LIVE`

## Explicit user approval

The user explicitly approved:

```text
Stage233として、MT5デモ口座でdemo発注ループを許可します。
SCALP候補は0.01 lot、DAYTRADE候補も0.01 lotで許可します。
GOLD#のみ、ORDER_FILLING_IOC、TP/SL必須、各signal_id 1回のみ、SCALP最大1ポジション、DAYTRADE最大1ポジション、合計最大2ポジションまで許可します。
実口座、final live、payload activation、NO_SIGNAL発注、無制限autotradeは許可しません。
```

## Basis

Stage232 passed dry-run:

```text
status=READY
runtime_queue_exists=True
runtime_queue_rows=0
open_gold_position_count=0
order_send_called=False
blocker_count=0
```

Stage231 reconciled the Stage230 single demo order and confirmed no current open position.

## Scope

Stage233 may:

```text
- run Stage227 queue refresh before reading runtime queue
- read FX_OUTPUTS/gold_v3/runtime/alert_only_queue.csv
- confirm MT5 DEMO account
- inspect current GOLD# positions
- place a DEMO order only for eligible queued SIGNAL rows
- write execution ledger and paste_me
```

Stage233 must not:

```text
- run on a real account
- send an order for NO_SIGNAL
- send more than one order per signal_id
- exceed SCALP max 1 open position
- exceed DAYTRADE max 1 open position
- exceed total max 2 open positions
- use symbols other than GOLD#
- use volume other than 0.01
- use filling other than ORDER_FILLING_IOC
- send without TP/SL
- enable final live
- activate payload trading
- run unlimited autotrade
```

## Role split

```text
SCALP:
  role match contains SCALP
  volume=0.01
  magic=30023301
  comment=G3S233_SCALP

DAYTRADE:
  non-SCALP SIGNAL, or role contains DAY/DAYTRADE
  volume=0.01
  magic=30023302
  comment=G3S233_DAY
```

## Runtime cadence

Default local loop is one cycle. A BAT may run one cycle after Stage227 refresh. A loop mode may use minute boundary + 5 seconds, but still bounded by max cycles supplied by the operator.

## Output files

```text
FX_OUTPUTS/gold_v3/233/demo_order_loop_scalp_daytrade_001lot/stage233_execution_ledger.csv
FX_OUTPUTS/gold_v3/233/demo_order_loop_scalp_daytrade_001lot/stage233_rejected_rows.csv
FX_OUTPUTS/gold_v3/233/demo_order_loop_scalp_daytrade_001lot/stage233_positions_snapshot.json
FX_OUTPUTS/gold_v3/233/demo_order_loop_scalp_daytrade_001lot/stage233_summary.json
FX_OUTPUTS/gold_v3/233/paste_me.txt
```

## Expected decision

```text
STAGE233_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT_READY
```

or blocked:

```text
STAGE233_DEMO_ORDER_LOOP_SCALP_DAYTRADE_001LOT_BLOCKED
```

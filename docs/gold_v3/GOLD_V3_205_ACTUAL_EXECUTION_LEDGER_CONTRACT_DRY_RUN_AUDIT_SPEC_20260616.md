# GOLD V3 Stage205 Actual Execution Ledger Contract Dry-Run Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage205 defines the actual execution ledger contract.

Final live performance should be reviewed by real execution results.

Theoretical M5 OHLC results remain useful to separate strategy logic from execution quality.

## Ledger separation

### trade_signal_ledger.csv

Signal occurrence and intended setup.

### theoretical_result_ledger.csv

M5 OHLC TP/SL/HORIZON resolution.

Used to judge strategy logic independent of real execution quality.

### actual_execution_ledger.csv

Actual MT5 order/deal/position history.

Used to judge real execution performance.

### execution_reconciliation_ledger.csv

Compares theoretical result against actual execution result.

Used to separate:

- strategy loss
- spread impact
- slippage impact
- commission impact
- swap impact
- delayed or missed execution

## Actual execution fields

- signal_id
- entry_dt
- role
- route
- candidate_id
- direction
- symbol
- account_id_hash
- broker_server
- magic_number
- order_id
- deal_id_entry
- deal_id_exit
- position_id
- order_type
- volume_lots
- requested_entry_price
- actual_entry_price
- entry_slippage_points
- entry_spread_points
- entry_commission
- requested_exit_price
- actual_exit_price
- exit_slippage_points
- exit_spread_points
- exit_commission
- swap
- gross_profit_account_ccy
- net_profit_account_ccy
- net_profit_points
- actual_open_time
- actual_close_time
- actual_holding_seconds
- actual_status
- actual_close_reason
- actual_comment

## Outputs

- `gold_v3_205_actual_execution_ledger_contract_sample.csv`
- `gold_v3_205_theoretical_result_ledger_contract_sample.csv`
- `gold_v3_205_execution_reconciliation_ledger_contract_sample.csv`
- `gold_v3_205_actual_execution_monthly_summary_schema.csv`
- `gold_v3_205_actual_execution_ledger_contract.md`
- `gold_v3_205_summary.json`
- `gold_v3_205_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- dry-run only
- no source CSV mutation
- no actual order import enabled
- no MT5 order placed
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify

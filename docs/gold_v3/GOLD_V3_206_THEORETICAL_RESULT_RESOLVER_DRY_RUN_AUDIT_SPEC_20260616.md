# GOLD V3 Stage206 Theoretical Result Resolver Dry-Run Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage206 resolves theoretical M5 OHLC outcomes for signal ledger rows.

It fills theoretical result fields only. Actual execution remains pending until future MT5 order/history export is available.

## Inputs

- Stage204 enriched trade signal ledger sample
- Stage205 decision
- M5 candles using Stage177 data-location contract

## Output fields

- signal_id
- entry_dt
- role
- route
- candidate_id
- direction
- entry_price
- tp
- sl
- horizon_m5
- theoretical_exit_dt
- theoretical_exit_price
- theoretical_hit_type
- theoretical_pnl_raw
- theoretical_pnl_cost3
- theoretical_pnl_cost5
- theoretical_r_multiple
- theoretical_holding_m5_bars
- theoretical_source
- source_stage

## Resolution rule

- M5 OHLC after the entry timestamp is used for theoretical outcome only.
- TP, SL, and HORIZON are resolved using the same audit convention used in prior stages.
- If TP and SL are touched in the same M5 bar, SL priority is applied.
- This is not an entry gate.
- This is not live approval.

## Outputs

- `gold_v3_206_source_coverage.csv`
- `gold_v3_206_theoretical_result_ledger_resolved_sample.csv`
- `gold_v3_206_execution_reconciliation_pending_actual_sample.csv`
- `gold_v3_206_theoretical_monthly_summary_sample.csv`
- `gold_v3_206_theoretical_result_resolver_plan.md`
- `gold_v3_206_summary.json`
- `gold_v3_206_decision.csv`
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

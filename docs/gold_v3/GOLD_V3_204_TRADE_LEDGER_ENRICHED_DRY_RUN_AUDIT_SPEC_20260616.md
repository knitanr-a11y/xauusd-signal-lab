# GOLD V3 Stage204 Trade Ledger Enriched Dry-Run Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage204 enriches the long-retention trade ledger dry-run design.

The goal is to make later review possible:

- why losses happened
- win rate
- PF
- trade count
- weak candidates
- weak time ranges
- cost stress impact

## Inputs

- Stage200 full tail96 preview
- Stage203 decision

Stage200 full tail is used because it still contains TP, SL, horizon, route, candidate, direction, and entry-time features.

## Enriched trade signal ledger fields

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
- rule_version
- source_stage
- cost_model
- m15_close
- h1_atr14
- d1_dist_close_atr28
- h4_body_atr14
- final_route
- send_action
- status
- created_at_utc
- audit_only

## Trade result ledger fields

- signal_id
- entry_dt
- exit_dt
- role
- route
- candidate_id
- direction
- entry_price
- exit_price
- tp
- sl
- horizon_m5
- result_status
- hit_type
- pnl_raw
- pnl_cost3
- pnl_cost5
- r_multiple
- holding_m5_bars
- close_reason
- loss_reason_tag
- review_note
- source_stage
- cost_model
- created_at_utc
- updated_at_utc
- audit_only

## Monthly summary fields

- month
- role
- route
- candidate_id
- trades
- wins
- losses
- open_or_pending
- win_rate_pct
- gross_profit
- gross_loss
- pf
- sum_pnl_cost3
- sum_pnl_cost5
- avg_pnl_cost3
- avg_pnl_cost5
- max_loss_streak
- weak_hour_notes
- loss_reason_top
- source_result_ledger
- updated_at_utc

## Outputs

- `gold_v3_204_trade_signal_ledger_enriched_sample.csv`
- `gold_v3_204_trade_result_ledger_schema_sample.csv`
- `gold_v3_204_trade_history_monthly_summary_schema_sample.csv`
- `gold_v3_204_trade_signal_ledger_validation_issues.csv`
- `gold_v3_204_trade_ledger_enriched_plan.md`
- `gold_v3_204_summary.json`
- `gold_v3_204_decision.csv`
- `paste_me.txt`

## Pass conditions

- blocker_count == 0
- signal ledger required fields are present
- signal ledger has no missing required TP/SL/Horizon values for signal rows
- no send
- no order
- no payload
- no live hook
- no autotrade

## Guardrails

- audit-only
- dry-run only
- no source CSV mutation
- no live file mutation outside Stage204 output directory
- no send
- no order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify

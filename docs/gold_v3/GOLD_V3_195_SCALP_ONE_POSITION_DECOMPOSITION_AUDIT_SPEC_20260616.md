# GOLD V3 Stage195 SCALP_ONE_POSITION Decomposition Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage195 decomposes the Stage193/194 `SCALP_ONE_POSITION` result.

The user prefers one-position counting over lot stacking, but wants to inspect why weak days occurred before considering any promotion.

## Source

Stage195 reads:

- `gold_v3_193_scalping_profit_stack_portfolio_trades.csv`
- `gold_v3_193_scalping_selected_profit_stack_watchlist.csv`

It may also copy the Stage194 one-position daily reference if available.

## Focus months

- 2026-05
- 2026-06

## Focus weak days

- 2026-05-20
- 2026-05-28
- 2026-06-02
- 2026-06-10
- 2026-06-15

## Decomposition axes

- daily summary
- negative-day summary
- candidate contribution
- direction contribution
- entry-hour contribution
- hit type by candidate
- focus-day trade detail
- top losses over all period

## Outputs

- `gold_v3_195_scalp_one_position_trades_all.csv`
- `gold_v3_195_scalp_one_position_trades_2026_05_06.csv`
- `gold_v3_195_scalp_one_position_overall_summary.csv`
- `gold_v3_195_scalp_one_position_monthly_summary.csv`
- `gold_v3_195_scalp_one_position_daily_2026_05_06.csv`
- `gold_v3_195_scalp_one_position_candidate_month_2026_05_06.csv`
- `gold_v3_195_scalp_one_position_direction_month_2026_05_06.csv`
- `gold_v3_195_scalp_one_position_hour_month_2026_05_06.csv`
- `gold_v3_195_scalp_one_position_focus_day_trade_detail.csv`
- `gold_v3_195_scalp_one_position_focus_day_candidate_breakdown.csv`
- `gold_v3_195_scalp_one_position_hit_type_by_candidate_2026_05_06.csv`
- `gold_v3_195_scalp_one_position_top_losses.csv`
- `gold_v3_195_scalp_one_position_worst_days_2026_05_06.csv`
- `gold_v3_195_stage194_one_position_daily_reference.csv`
- `gold_v3_195_summary.json`
- `gold_v3_195_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- review-only
- no source CSV mutation
- no contract mutation
- no open/as-of interpretation
- no candidate pool removal
- no F002 bypass
- no final live approval
- no Discord notification
- no MT5 order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify Discord

No filter or candidate is promoted in this stage.

# GOLD V3 Stage196 SCALP_ONE_POSITION Full-Period Filter Sensitivity Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage196 tests whether weak filters for `SCALP_ONE_POSITION` are valid over the full period.

The user correctly noted that time restrictions cannot be judged from only 2026-05/2026-06 weak days.

Therefore the primary decision basis is full-period performance.

## Source

Stage196 reads:

- `gold_v3_193_scalping_profit_stack_portfolio_trades.csv`
- `gold_v3_193_scalping_selected_profit_stack_watchlist.csv`

## Tested filter families

- single MT5 hour exclusion across the full period
- grouped MT5 hour exclusion across the full period
- candidate-specific hour exclusion across the full period
- h1_atr14 cap sensitivity
- daily maximum trade count
- candidate daily maximum count
- same-candidate cooldown

## Primary viability rule

A filter is only viable if it passes all of the following:

- full-period net profit is not reduced
- full-period PF is not worsened
- test profit remains positive
- recent3m profit remains positive
- negative month count is not increased
- at least 70% of full-period trades remain

2026-05/2026-06 and weak-day improvements are reported but cannot alone justify a filter.

## Outputs

- `gold_v3_196_filter_sensitivity_all_results.csv`
- `gold_v3_196_filter_sensitivity_viable_full_period_first.csv`
- `gold_v3_196_best_filter_trades.csv`
- `gold_v3_196_best_filter_monthly_compare.csv`
- `gold_v3_196_base_summary.csv`
- `gold_v3_196_summary.json`
- `gold_v3_196_decision.csv`
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

No filter is promoted automatically in this stage.

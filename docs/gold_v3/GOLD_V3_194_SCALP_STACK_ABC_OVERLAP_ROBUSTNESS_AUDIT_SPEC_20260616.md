# GOLD V3 Stage194 SCALP_STACK / ABC Overlap Robustness Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage194 checks whether the Stage193 SCALP_STACK watchlist can coexist with the ABC PRIMARY portfolio.

It does not promote SCALP_STACK to PRIMARY.

## Inputs

Stage194 rebuilds ABC from closed OHLC using the Stage187/188 candidate definitions:

1. `A_PRECISION_BASE`
2. `C_BALANCED_CAP60`
3. `B_HIGH_FREQUENCY_CAP40`

Stage194 reads SCALP_STACK from Stage193:

- `gold_v3_193_scalping_selected_profit_stack_watchlist.csv`
- `gold_v3_193_scalping_profit_stack_portfolio_trades.csv`

## Checks

- ABC-only portfolio performance
- SCALP_STACK-only performance
- Combined independent performance
- Combined resolved portfolio with ABC priority first
- Combined resolved portfolio with SCALP priority first
- Exact same entry timestamp overlap
- Active ABC window overlap
- ABC/SCALP direction conflict count
- cost3 and cost5 stress
- weak month details for 2025-05, 2025-08, 2025-12

## Cost basis

Primary cost:

- `cost_points = 3.0`

Stress cost:

- `cost_points = 5.0`

## Outputs

- `gold_v3_194_source_coverage.csv`
- `gold_v3_194_scalp_stack_selected_reference.csv`
- `gold_v3_194_scalp_stack_portfolio_trades_reference.csv`
- `gold_v3_194_abc_portfolio_trades_rebuilt.csv`
- `gold_v3_194_exact_entry_overlap_abc_scalp.csv`
- `gold_v3_194_active_window_overlap_abc_scalp.csv`
- `gold_v3_194_combined_independent_no_overlap_control.csv`
- `gold_v3_194_combined_resolved_abc_priority_first.csv`
- `gold_v3_194_combined_resolved_scalp_priority_first.csv`
- `gold_v3_194_portfolio_summary_cost3_cost5.csv`
- `gold_v3_194_monthly_summary_cost3.csv`
- `gold_v3_194_weak_month_detail.csv`
- `gold_v3_194_stage193_scalp_monthly_reference.csv`
- `gold_v3_194_summary.json`
- `gold_v3_194_decision.csv`
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

ABC and SCALP_STACK remain separate audit families until further approval.

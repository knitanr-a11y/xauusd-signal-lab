# GOLD V3 Stage193 Scalping Profit Stack Portfolio Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage193 corrects the Stage192 interpretation.

The user does not want simple frequency inflation. The intended idea is:

> stack multiple high profit-rate scalping candidates so total opportunities increase through independent quality candidates.

Stage193 therefore evaluates candidate stacking at portfolio level.

## Source

Stage193 reads Stage191 outputs:

- `gold_v3_191_scalping_top_cost_sensitivity.csv`
- `gold_v3_191_scalping_top_trades_cost3.csv`
- `gold_v3_191_scalping_top_monthly_cost3.csv`
- `gold_v3_191_source_coverage.csv`

## Candidate filter

A candidate can enter the profit-stack pool if:

- full_n >= 120
- test_n >= 30
- recent3m_n >= 10
- train/test/full/recent3m net sums are positive
- full_pf >= 1.45
- test_pf >= 1.45
- recent3m_pf >= 1.20
- full_neg_months <= 5

These thresholds are intentionally not pure frequency thresholds.

## Stacking method

1. Rank candidates by profit-rate score:
   - net profit
   - PF
   - average net per trade
   - test and recent3m contribution
   - negative month penalty

2. Build greedy portfolio stack:
   - start from the best candidate
   - add candidates only if portfolio score improves
   - use resolved-priority de-duplication so overlapping open trades do not inflate count
   - priority within overlaps is the candidate profit-rate score

3. Compare stack scenarios:
   - independent sum without overlap control
   - resolved-priority portfolio with overlap control

## Outputs

- `gold_v3_193_scalping_candidate_profit_rate_ranking.csv`
- `gold_v3_193_scalping_selected_profit_stack_watchlist.csv`
- `gold_v3_193_scalping_greedy_stack_steps.csv`
- `gold_v3_193_scalping_stack_scenarios.csv`
- `gold_v3_193_scalping_profit_stack_portfolio_trades.csv`
- `gold_v3_193_scalping_profit_stack_monthly.csv`
- `gold_v3_193_source_coverage_from_stage191.csv`
- `gold_v3_193_stage191_monthly_reference.csv`
- `gold_v3_193_summary.json`
- `gold_v3_193_decision.csv`
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

The resulting stack is WATCHLIST only and must pass later robustness, ABC overlap, and live parity audits before promotion.

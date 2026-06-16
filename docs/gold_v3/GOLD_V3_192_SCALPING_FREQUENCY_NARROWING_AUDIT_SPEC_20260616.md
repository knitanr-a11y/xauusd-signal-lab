# GOLD V3 Stage192 Scalping Frequency Narrowing Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage192 re-ranks Stage191 scalping candidates with a frequency-first objective because the user wants more scalping trade opportunities.

The purpose is to find scalping WATCHLIST candidates that increase trade count while still retaining net profit after cost3.

No candidate is promoted to PRIMARY in this stage.

## Source

Stage192 reads Stage191 outputs:

- `gold_v3_191_scalping_search_results_top5000.csv`
- `gold_v3_191_scalping_eligible_profit_candidates.csv`
- `gold_v3_191_source_coverage.csv`

If Stage191 outputs are missing, Stage192 blocks and asks to run Stage191 first.

## Frequency-first criteria

High-frequency candidate baseline:

- full_n >= 300
- test_n >= 100
- recent3m_n >= 30
- train/test/full/recent3m net sums all positive
- full_pf >= 1.20
- test_pf >= 1.20
- recent3m_pf >= 1.10
- full_neg_months <= 6

Balanced high-frequency candidate:

- high-frequency baseline
- full_pf >= 1.50
- test_pf >= 1.50
- recent3m_pf >= 1.50
- full_neg_months <= 4

Small-TP high-frequency candidate:

- high-frequency baseline
- TP <= 10

## Objective

Frequency score prioritizes:

1. full_n
2. test_n
3. recent3m_n
4. full/test/recent3m net profit after cost3
5. full/test/recent3m PF
6. penalty for negative months

## Outputs

- `gold_v3_192_scalping_frequency_ranked_top2000.csv`
- `gold_v3_192_scalping_high_frequency_candidates.csv`
- `gold_v3_192_scalping_balanced_high_frequency_candidates.csv`
- `gold_v3_192_scalping_small_tp_frequency_candidates.csv`
- `gold_v3_192_scalping_selected_frequency_watchlist.csv`
- `gold_v3_192_scalping_profile_frequency_summary.csv`
- `gold_v3_192_stage191_eligible_reference.csv`
- `gold_v3_192_source_coverage_from_stage191.csv`
- `gold_v3_192_summary.json`
- `gold_v3_192_decision.csv`
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

Further monthly robustness, ABC overlap, cost sensitivity, and live parity are required before any scalping candidate is used live.

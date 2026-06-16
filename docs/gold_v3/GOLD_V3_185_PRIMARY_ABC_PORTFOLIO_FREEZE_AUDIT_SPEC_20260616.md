# GOLD V3 Stage185 Primary ABC Portfolio Freeze Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage185 treats A, B, and C as primary candidates, not secondary or optional candidates.

C uses the Stage184 improved cap version:

`h1_atr14 <= 60`

## Primary candidates

### A_PRECISION_BASE

- role: PRIMARY
- priority: 1
- rule: `d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`
- direction: LONG
- TP/SL: 40 / 20
- horizon_m5: 192

### B_HIGH_FREQUENCY

- role: PRIMARY
- priority: 3
- rule: `d1_dist_close_atr28<=-0.394892`
- direction: LONG
- TP/SL: 50 / 30
- horizon_m5: 192

### C_BALANCED_CAP60

- role: PRIMARY
- priority: 2
- rule: `d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60`
- direction: LONG
- TP/SL: 30 / 30
- horizon_m5: 192

## Outputs

- `gold_v3_185_primary_abc_candidates.json`
- `gold_v3_185_primary_abc_candidates.csv`
- `gold_v3_185_candidate_summary.csv`
- `gold_v3_185_trades_by_candidate.csv`
- `gold_v3_185_monthly_by_candidate.csv`
- `gold_v3_185_overlap_entry_timestamps.csv`
- `gold_v3_185_overlap_distribution.csv`
- `gold_v3_185_priority_unique_portfolio_trades.csv`
- `gold_v3_185_priority_unique_portfolio_monthly.csv`
- `gold_v3_185_summary.json`
- `gold_v3_185_decision.csv`
- `paste_me.txt`

## Interpretation

Stage185 does not approve live execution. It freezes the three primary candidate definitions for audit review and reports overlap among candidate entry timestamps.

The priority unique portfolio is only an audit view for duplicate timestamp review. It is not live execution approval.

## Guardrails

- audit-only
- no source CSV mutation
- no contract mutation
- no open/as-of allowance
- no candidate pool removal
- no F002 bypass
- no final live
- no Discord
- no MT5 order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL Discord notification remains off

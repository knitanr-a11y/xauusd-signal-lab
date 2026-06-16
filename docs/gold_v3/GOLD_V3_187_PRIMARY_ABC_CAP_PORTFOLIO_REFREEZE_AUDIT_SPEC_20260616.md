# GOLD V3 Stage187 Primary ABC Cap Portfolio Refreeze Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage187 refreezes the three PRIMARY candidates after applying the volatility caps found in Stage184 and Stage186.

- A remains unchanged.
- B uses the Stage186 `h1_atr14 <= 40` cap.
- C uses the Stage184 `h1_atr14 <= 60` cap.

## Primary candidates

### A_PRECISION_BASE

- role: PRIMARY
- rule: `d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`
- direction: LONG
- TP/SL: 40 / 20
- horizon_m5: 192

### B_HIGH_FREQUENCY_CAP40

- role: PRIMARY
- rule: `d1_dist_close_atr28<=-0.394892 & h1_atr14<=40`
- direction: LONG
- TP/SL: 50 / 30
- horizon_m5: 192

### C_BALANCED_CAP60

- role: PRIMARY
- rule: `d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60`
- direction: LONG
- TP/SL: 30 / 30
- horizon_m5: 192

## Priority audit views

Stage187 reports two duplicate-entry audit views:

- `ACB_PRIORITY_A_GT_C_GT_B`
- `CAB_PRIORITY_C_GT_A_GT_B`

These are audit views only. They are not live execution approval.

## Outputs

- `gold_v3_187_primary_abc_cap_candidates.json`
- `gold_v3_187_primary_abc_cap_candidates.csv`
- `gold_v3_187_candidate_summary.csv`
- `gold_v3_187_trades_by_candidate.csv`
- `gold_v3_187_monthly_by_candidate.csv`
- `gold_v3_187_overlap_entry_timestamps.csv`
- `gold_v3_187_overlap_distribution.csv`
- `gold_v3_187_priority_portfolio_summary.csv`
- `gold_v3_187_priority_portfolio_monthly_all.csv`
- priority-scenario trade and monthly CSVs
- `gold_v3_187_summary.json`
- `gold_v3_187_decision.csv`
- `paste_me.txt`

## Guardrails

Stage187 is audit-only.

No source CSV mutation, contract mutation, open/as-of allowance, candidate pool removal, F002 bypass, live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.

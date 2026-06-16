# GOLD V3 Stage182 Candidate Portfolio Monthly Compare Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage182 compares three fixed candidate variants side by side by month:

1. `A_PRECISION_BASE`
   - rule: `d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`
   - LONG TP40 / SL20 / horizon_m5 192

2. `B_HIGH_FREQUENCY`
   - rule: `d1_dist_close_atr28<=-0.394892`
   - LONG TP50 / SL30 / horizon_m5 192

3. `C_BALANCED`
   - rule: `d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008`
   - LONG TP30 / SL30 / horizon_m5 192

## Inputs

OHLC candles using the Stage177 data-location contract:

- 2025 historical: `Files/FX_OUTPUTS/mt5_candles/gold_2025/gold#_<tf>.csv`
- live/continuation: `Files/goldsharp_<tf>.csv`

## Metrics

For each candidate:

- dedup trade count
- train/test/full PF
- train/test/full win rate
- recent3m PF and win rate
- full negative months
- worst month
- TP/SL/horizon exit counts
- monthly trades/wins/losses/win_rate/PF/pnl_sum

Cost points default to 3.0.

## Outputs

- `gold_v3_182_candidate_summary.csv`
- `gold_v3_182_monthly_by_candidate.csv`
- `gold_v3_182_yearly_by_candidate.csv`
- `gold_v3_182_monthly_pivot.csv`
- `gold_v3_182_dedup_trades_by_candidate.csv`
- `gold_v3_182_summary.json`
- `gold_v3_182_decision.csv`
- `paste_me.txt`

## Guardrails

Audit-only. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.

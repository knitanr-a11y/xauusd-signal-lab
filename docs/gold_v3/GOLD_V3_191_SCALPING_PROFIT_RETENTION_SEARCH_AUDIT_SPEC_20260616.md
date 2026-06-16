# GOLD V3 Stage191 Scalping Profit Retention Search Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage191 explores adding scalping-style candidates to GOLD V3.

The objective is not raw win rate. The objective is whether net profit remains after costs.

Primary evaluation cost:

- `cost_points = 3.0`

Cost sensitivity:

- `0.0`
- `1.0`
- `2.0`
- `3.0`
- `5.0`

## TP/SL profiles

TP is never below 5.0.

- TP5 / SL2.5 / horizon12 M5 bars
- TP5 / SL2.5 / horizon24 M5 bars
- TP5 / SL2.5 / horizon48 M5 bars
- TP7.5 / SL2.5 / horizon24
- TP7.5 / SL3.0 / horizon36
- TP10 / SL3.5 / horizon36
- TP10 / SL5 / horizon48
- TP12.5 / SL5 / horizon64
- TP15 / SL5 / horizon64

Both LONG and SHORT are tested.

## Search method

The script builds closed OHLC-derived features with the Stage177 feature contract, then tests single and pair rule conditions over selected entry-available features.

M5 future bars are used only after entry detection for audit TP/SL/horizon scoring.

## Ranking objective

Ranking prioritizes:

1. net full-period profit after cost3;
2. net test-period profit after cost3;
3. net recent3m profit after cost3;
4. PF robustness;
5. low or zero negative months;
6. adequate trade count.

Raw win rate is reported but is not the primary objective.

## Outputs

- `gold_v3_191_condition_library.csv`
- `gold_v3_191_scalping_search_results_top5000.csv`
- `gold_v3_191_scalping_eligible_profit_candidates.csv`
- `gold_v3_191_scalping_top_cost_sensitivity.csv`
- `gold_v3_191_scalping_top_trades_cost3.csv`
- `gold_v3_191_scalping_top_monthly_cost3.csv`
- `gold_v3_191_source_coverage.csv`
- `gold_v3_191_summary.json`
- `gold_v3_191_decision.csv`
- `paste_me.txt`

## Guardrails

Stage191 is audit-only.

- no source CSV mutation
- no contract mutation
- no open/as-of interpretation
- no candidate pool removal
- no F002 bypass
- no final live signal approval
- no Discord notification
- no MT5 order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify Discord

No scalping candidate may be promoted without later robustness and live-parity audit.

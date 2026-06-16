# GOLD V3 Stage183 February Weakness Breakdown Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage183 investigates the February 2026 weakness observed in the fixed ABC candidates from Stage182.

The goal is to determine whether the weakness is:

- broad across all candidates;
- specific to B or C;
- concentrated by date, week, hour, or day of week;
- associated with entry-time OHLC-derived feature differences;
- merely a temporary month-level drawdown that remains acceptable.

## Fixed candidates

Same as Stage182:

- `A_PRECISION_BASE`
- `B_HIGH_FREQUENCY`
- `C_BALANCED`

## Focus month

- `2026-02`

## Compare months

- `2026-01`
- `2026-02`
- `2026-03`
- `2026-04`
- `2026-05`
- `2026-06`

## Outputs

- `gold_v3_183_focus_month_summary.csv`
- `gold_v3_183_2026_month_compare_summary.csv`
- `gold_v3_183_focus_month_by_day.csv`
- `gold_v3_183_focus_month_by_week.csv`
- `gold_v3_183_focus_month_by_hour.csv`
- `gold_v3_183_focus_month_by_dow.csv`
- `gold_v3_183_focus_month_feature_win_loss.csv`
- `gold_v3_183_focus_month_trades.csv`
- `gold_v3_183_replayed_trades_all.csv`
- `gold_v3_183_summary.json`
- `gold_v3_183_decision.csv`
- `paste_me.txt`

## Guardrails

Stage183 is audit-only. It does not create or approve live signals.

No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.

Post-entry M5 outcomes are used only for audit scoring, not for entry conditions.

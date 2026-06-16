# GOLD V3 Stage197 SCALP_ONE_POSITION_FILTERED_V1 Freeze Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage197 freezes the best Stage196 scalping filter as an audit-only review candidate.

Candidate name:

`SCALP_ONE_POSITION_FILTERED_V1`

Definition:

- Start from Stage193 selected SCALP one-position stack.
- Apply only one filter:
  - `SCALP_002_tp15_sl5_hz64_SHORT` is excluded when MT5 `entry_hour == 09`.
- Re-run one-position priority resolution after the filter.

## Inputs

- Stage193 selected watchlist:
  - `gold_v3_193_scalping_selected_profit_stack_watchlist.csv`
- Stage191 raw selected trades:
  - `gold_v3_191_scalping_top_trades_cost3.csv`
- Closed OHLC rebuilt through Stage177 contract.

## Checks

- raw selected trades before filter
- raw trades removed by filter
- filtered raw selected trades
- rebuilt one-position filtered portfolio
- base one-position comparison
- ABC rebuilt portfolio
- combined ABC-priority-first portfolio
- combined SCALP-priority-first portfolio
- cost3 and cost5 summaries
- monthly summaries
- 2026-05 / 2026-06 daily counts
- exact and active-window overlap with ABC
- latest closed M15 detector snapshot
- detector/raw-entry parity check

## Outputs

- `gold_v3_197_selected_scalp_watchlist_reference.csv`
- `gold_v3_197_scalp_raw_selected_before_filter.csv`
- `gold_v3_197_scalp_raw_selected_after_filtered_v1.csv`
- `gold_v3_197_scalp_raw_removed_by_filtered_v1.csv`
- `gold_v3_197_scalp_one_position_base_rebuilt.csv`
- `gold_v3_197_scalp_one_position_filtered_v1_trades.csv`
- `gold_v3_197_abc_portfolio_trades_rebuilt.csv`
- `gold_v3_197_combined_raw_abc_plus_filtered_scalp.csv`
- `gold_v3_197_combined_abc_priority_first.csv`
- `gold_v3_197_combined_scalp_priority_first.csv`
- `gold_v3_197_exact_entry_overlap_abc_filtered_scalp.csv`
- `gold_v3_197_active_window_overlap_abc_filtered_scalp.csv`
- `gold_v3_197_portfolio_summary_cost3_cost5.csv`
- `gold_v3_197_monthly_summary_cost3.csv`
- `gold_v3_197_daily_counts_2026_05_06_cost3.csv`
- `gold_v3_197_latest_detector_tail96.csv`
- `gold_v3_197_detector_raw_entry_parity.csv`
- `gold_v3_197_source_coverage.csv`
- `gold_v3_197_summary.json`
- `gold_v3_197_decision.csv`
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

ABC remains PRIMARY. `SCALP_ONE_POSITION_FILTERED_V1` remains SECONDARY/WATCHLIST until explicit later approval.

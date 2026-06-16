# GOLD V3 Stage198 SCALP_FILTERED_V1 OHLC Parity Reconciliation Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage198 answers the user question:

Can `SCALP_ONE_POSITION_FILTERED_V1` be reproduced from OHLC?

It separates two issues:

1. OHLC detector and M5 OHLC scoring reproducibility.
2. Differences against the older Stage191 trade artifact.

## Source

- Stage193 selected scalping watchlist:
  - `gold_v3_193_scalping_selected_profit_stack_watchlist.csv`
- Stage191 artifact:
  - `gold_v3_191_scalping_top_trades_cost3.csv`
- Closed OHLC rebuilt through Stage177 contract.

## Filter under test

`SCALP_ONE_POSITION_FILTERED_V1`:

- selected Stage193 scalping candidates
- exclude `SCALP_002_tp15_sl5_hz64_SHORT` when MT5 `entry_hour == 09`

## Reconciliation steps

1. Build selected candidate entries from closed OHLC features.
2. Apply the FILTERED_V1 hour rule.
3. Recompute TP/SL/horizon outcome using M5 OHLC after entry.
4. Compare detector entries vs recomputed scored rows.
5. Compare recomputed scored rows vs Stage191 artifact rows.
6. Compare one-position resolved rows between recomputed and Stage191 artifact.
7. Classify recomputed-only rows.

## Outputs

- `gold_v3_198_source_coverage.csv`
- `gold_v3_198_stage191_selected_before_filter.csv`
- `gold_v3_198_stage191_selected_after_filtered_v1.csv`
- `gold_v3_198_stage191_removed_by_filtered_v1.csv`
- `gold_v3_198_ohlc_detector_entries_before_filter.csv`
- `gold_v3_198_ohlc_detector_entries_after_filtered_v1.csv`
- `gold_v3_198_ohlc_detector_removed_by_filtered_v1.csv`
- `gold_v3_198_ohlc_recomputed_scored_trades_before_filter.csv`
- `gold_v3_198_ohlc_recomputed_scored_trades_after_filtered_v1.csv`
- `gold_v3_198_ohlc_recomputed_removed_by_filtered_v1.csv`
- `gold_v3_198_stage191_filtered_v1_one_position.csv`
- `gold_v3_198_ohlc_recomputed_filtered_v1_one_position.csv`
- `gold_v3_198_parity_comparison_summary.csv`
- `gold_v3_198_detector_vs_recomputed_left_only.csv`
- `gold_v3_198_detector_vs_recomputed_right_only.csv`
- `gold_v3_198_recomputed_vs_stage191_artifact_left_only.csv`
- `gold_v3_198_recomputed_vs_stage191_artifact_right_only.csv`
- `gold_v3_198_one_position_recomputed_vs_stage191_left_only.csv`
- `gold_v3_198_one_position_recomputed_vs_stage191_right_only.csv`
- `gold_v3_198_recomputed_only_vs_stage191_classified.csv`
- `gold_v3_198_recomputed_only_classification_counts.csv`
- `gold_v3_198_recomputed_only_by_month_candidate.csv`
- `gold_v3_198_summary.json`
- `gold_v3_198_decision.csv`
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

M5 future data is used only after entry for audit scoring, never for entry detection.

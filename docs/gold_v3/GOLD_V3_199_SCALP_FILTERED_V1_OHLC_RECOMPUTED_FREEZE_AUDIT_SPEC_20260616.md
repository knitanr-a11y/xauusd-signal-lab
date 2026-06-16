# GOLD V3 Stage199 SCALP_FILTERED_V1 OHLC-Recomputed Freeze Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage199 makes the Stage198 OHLC-recomputed route the audit comparison basis for the scalping secondary audit candidate.

Candidate name:

`SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED`

## Background

Stage198 showed:

- detector vs OHLC recomputed scored rows: parity pass
- OHLC recomputed rows vs older Stage191 artifact: artifact-scope mismatch

Therefore Stage199 no longer treats the Stage191 artifact as the scoring source for the frozen scalping review candidate.

## Definition

`SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED`:

- uses Stage193 selected scalping candidates
- detects entries from closed M15/H1/H4/D1 OHLC-derived features
- excludes `SCALP_002_tp15_sl5_hz64_SHORT` when MT5 `entry_hour == 09`
- scores TP/SL/horizon from M5 OHLC after entry for audit only
- resolves to one active scalp position by selected candidate priority

## Checks

- full/train/test/recent3m metrics
- cost3 and cost5 metrics
- monthly summary
- 2026-05 and 2026-06 daily count summary
- raw removed rows by the filtered V1 rule
- ABC rebuilt portfolio
- ABC-priority-first combined portfolio
- SCALP-priority-first combined portfolio
- exact/active-window overlap with ABC
- latest closed M15 detector snapshot
- Stage197 artifact-based comparison deltas
- handoff markdown

## Outputs

- `gold_v3_199_source_coverage.csv`
- `gold_v3_199_scalp_detector_entries_before_filter.csv`
- `gold_v3_199_scalp_ohlc_recomputed_scored_before_filter.csv`
- `gold_v3_199_scalp_ohlc_recomputed_scored_after_filtered_v1.csv`
- `gold_v3_199_scalp_ohlc_recomputed_removed_by_filtered_v1.csv`
- `gold_v3_199_scalp_filtered_v1_ohlc_recomputed_one_position.csv`
- `gold_v3_199_abc_portfolio_rebuilt.csv`
- `gold_v3_199_combined_raw_abc_plus_ohlc_scalp.csv`
- `gold_v3_199_combined_abc_priority_first_ohlc_scalp.csv`
- `gold_v3_199_combined_scalp_priority_first_ohlc_scalp.csv`
- `gold_v3_199_exact_entry_overlap_abc_ohlc_scalp.csv`
- `gold_v3_199_active_window_overlap_abc_ohlc_scalp.csv`
- `gold_v3_199_portfolio_summary_cost3_cost5.csv`
- `gold_v3_199_monthly_summary_cost3.csv`
- `gold_v3_199_daily_counts_2026_05_06_cost3.csv`
- `gold_v3_199_latest_detector_tail96.csv`
- `gold_v3_199_compare_against_stage197_artifact_based.csv`
- `gold_v3_199_handoff.md`
- `gold_v3_199_summary.json`
- `gold_v3_199_decision.csv`
- `paste_me.txt`

## Terminology

Do not classify this scalping candidate as a watchlist.

Use one of the following terms instead:

- `SECONDARY_AUDIT_CANDIDATE`
- `SCALP_SECONDARY_CANDIDATE`
- `補助戦略候補`

ABC remains the PRIMARY portfolio. The scalping candidate remains audit-only and secondary until explicit later approval.

## Cost interpretation

- `cost3` means a 3.0 price-point per-trade friction assumption.
- `cost5` means a 5.0 price-point per-trade stress assumption.
- The cost value is not spread-only. It is an all-in execution friction proxy that can include wider spread, slippage, commission conversion, and other execution drag.
- In practice, cost5 should be read as a wider-spread / worse-execution stress test.

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

ABC remains PRIMARY. The scalping candidate remains SECONDARY_AUDIT_CANDIDATE until explicit later approval.
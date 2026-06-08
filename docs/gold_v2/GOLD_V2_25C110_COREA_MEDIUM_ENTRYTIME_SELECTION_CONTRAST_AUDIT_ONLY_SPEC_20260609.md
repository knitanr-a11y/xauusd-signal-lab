# GOLD V2 25C110 CoreA/MEDIUM entry-time selection contrast audit-only spec

Created: 2026-06-09

Status: `COREA_MEDIUM_ENTRYTIME_SELECTION_CONTRAST_SPEC_READY_AUDIT_ONLY`

## Purpose

25C109 confirmed that the primary CoreA and MEDIUM replay target artifacts are readable:

```text
CoreA primary:  gold_v2_13b_corea_selected_source_rows.csv
MEDIUM primary: gold_v2_13d_medium_selected_after_internal_priority.csv
```

Both primary targets contain future/profit/selection columns. 25C110 performs a fast contrast against the corresponding source universe files to test whether selected/final rows can be identified from entry-time columns alone.

This is still a lightweight audit. It does not replay OHLC and does not implement live logic.

## Inputs

Use local 25C109 outputs:

```text
25c109_summary.json
25c109_primary_replay_targets.csv
25c109_target_load_matrix.csv
```

Required upstream status:

```text
25c109_summary.status = COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_READY_AUDIT_ONLY_LIVE_BLOCKED
```

## Source universe pairing

CoreA:

```text
selected: gold_v2_13b_corea_selected_source_rows.csv
universe:  gold_v2_13b_corea_source_cluster_ledger_normalized.csv
```

MEDIUM:

```text
selected: gold_v2_13d_medium_selected_after_internal_priority.csv
universe:  gold_v2_13d_medium_source_rows_with_manifest_match.csv
```

If preferred universe file is unavailable, locate highest-ranked readable target in the same component with rows >= selected rows.

## Entry-time signature

Use common columns between selected and universe after excluding:

Future/outcome:

```text
exit_time, top_exit_time, close_time, outcome, result, win, loss, hit, mae, mfe, realized
```

Profit/representative:

```text
profit, profit_r, selected_profit, selected_profit_r, top_profit, top_profit_r, pnl, profit_*_from_members, stacked_*profit*
```

Selection/arbitration:

```text
selected, top_candidate_id, top_variant, top_direction, final_sot, arbitration, priority, chosen, prefer, is_*selected
```

Also exclude pure hash/path/report columns:

```text
hash, path, file, report, status, reason
```

Keep entry-time candidates such as:

```text
entry_time, top_entry_time, direction, dataset, strategy_id, range96, ret96, trend_eff96, tr_mean_32, regime, count, score, condition, filter
```

## Metrics

For each component:

```text
selected_rows
universe_rows
entry_signature_columns
selected_rows_with_no_universe_match
selected_rows_with_unique_universe_match
selected_rows_with_ambiguous_universe_match
ambiguous_match_ratio
universe_rows_in_selected_signature_groups
universe_rows_not_in_selected_signature_groups
selected_signature_groups
selected_signature_groups_with_multiple_selected_rows
```

Interpretation:

- If many selected rows have ambiguous universe matches under entry-time columns, selected/final cannot be proven entry-time reproducible without additional non-entry or post-entry columns.
- If selected signatures are unique only with highly specific time/price/ID columns, this remains a review blocker.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c110_corea_medium_entrytime_selection_contrast_audit_only
```

Output files:

```text
GOLD_V2_25C110_COREA_MEDIUM_ENTRYTIME_SELECTION_CONTRAST_AUDIT_ONLY_REPORT.md
25c110_summary.json
25c110_pair_inventory.csv
25c110_entrytime_contrast_summary.csv
25c110_ambiguous_selected_rows.csv
25c110_entry_signature_columns.csv
25c110_decision_matrix.csv
25c110_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c110_corea_medium_entrytime_selection_contrast_audit_only.zip
```

## Status names

If inputs are missing or upstream status fails:

```text
COREA_MEDIUM_ENTRYTIME_SELECTION_CONTRAST_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If both CoreA and MEDIUM pairs are readable and either has ambiguous ratio > 0:

```text
COREA_MEDIUM_ENTRYTIME_SELECTION_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If both pairs are readable and selected rows map uniquely to universe rows by entry-time signature:

```text
COREA_MEDIUM_ENTRYTIME_SELECTION_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even unique candidate remains audit-only and live blocked.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not treat entry-time uniqueness as source recovery approval.

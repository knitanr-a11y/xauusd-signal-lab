# GOLD V2 25C109 CoreA/MEDIUM target artifact feasibility audit-only spec

Created: 2026-06-09

Status: `COREA_MEDIUM_TARGET_ARTIFACT_FEASIBILITY_SPEC_READY_AUDIT_ONLY`

## Purpose

25C108 shortlisted 13 CoreA/MEDIUM replay targets. 25C109 reads those target artifacts directly and creates a small feasibility matrix before any OHLC replay.

This answers:

```text
Which target files are actually readable locally?
Which target files contain direct future/outcome/profit/selection columns?
Which one CoreA target and which one MEDIUM target should be replayed first?
```

This is audit-only. It does not approve source recovery and does not implement live logic.

## Inputs

Use local 25C108 outputs:

```text
25c108_summary.json
25c108_replay_target_shortlist.csv
25c108_target_column_risk_rows.csv
25c108_component_replay_scope.csv
```

Required upstream status:

```text
25c108_summary.status = COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_READY_AUDIT_ONLY_LIVE_BLOCKED
```

For each target path in `25c108_replay_target_shortlist.csv`, read the CSV or JSON target if it exists.

If an absolute Windows path is not readable, try to locate the file by basename under:

```text
repo root
Files root
Files/FX_OUTPUTS
```

## Columns/classes

Forbidden/future/outcome columns:

```text
exit_time, top_exit_time, close_time, outcome, result, win, loss, hit, mae, mfe, realized
```

Profit/representative columns:

```text
profit, profit_r, selected_profit, selected_profit_r, top_profit, top_profit_r, stacked_*profit*, profit_*_from_members
```

Selection/arbitration columns:

```text
selected, top_candidate_id, top_variant, top_direction, final_sot, arbitration, priority, is_*selected
```

Entry-time candidates:

```text
entry_time, top_entry_time, direction, dataset, strategy_id, range96, ret96, trend_eff96, tr_mean_32, regime, count, score, condition, filter
```

## Primary target recommendation

Pick one CoreA and one MEDIUM artifact for the next replay.

Preferred CoreA target:

```text
gold_v2_13b_corea_selected_source_rows.csv
```

Preferred MEDIUM target:

```text
gold_v2_13d_medium_selected_after_internal_priority.csv
```

If unavailable, use highest risk-score readable target in that component.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c109_corea_medium_target_artifact_feasibility_audit_only
```

Output files:

```text
GOLD_V2_25C109_COREA_MEDIUM_TARGET_ARTIFACT_FEASIBILITY_AUDIT_ONLY_REPORT.md
25c109_summary.json
25c109_target_load_matrix.csv
25c109_target_column_family_matrix.csv
25c109_primary_replay_targets.csv
25c109_decision_matrix.csv
25c109_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c109_corea_medium_target_artifact_feasibility_audit_only.zip
```

## Status names

If inputs are missing or upstream fails:

```text
COREA_MEDIUM_TARGET_ARTIFACT_FEASIBILITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If both CoreA and MEDIUM primary replay targets are readable:

```text
COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_READY_AUDIT_ONLY_LIVE_BLOCKED
```

If only one side is readable:

```text
COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_PARTIAL_AUDIT_ONLY_LIVE_BLOCKED
```

If neither side is readable:

```text
COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_UNREADABLE_AUDIT_ONLY_LIVE_BLOCKED
```

Even READY remains audit-only and live blocked.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not treat target readability as replay proof.

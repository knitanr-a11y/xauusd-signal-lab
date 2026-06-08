# GOLD V2 25C108 CoreA/MEDIUM replay target shortlist audit-only spec

Created: 2026-06-09

Status: `COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_SPEC_READY_AUDIT_ONLY`

## Purpose

25C107 confirmed that actual GOLD V2 CoreA/MEDIUM SOT/final/selected/arbitration artifacts contain hard-future, profit/representative, and selection/arbitration columns.

25C108 narrows 25C107 to a small replay target shortlist. It does not replay OHLC and does not implement live logic. It chooses the first artifacts that should be manually/deeply replayed to verify entry-time reproducibility.

This keeps the process short and avoids another broad scan.

## Source-of-truth inputs

Use local 25C107 outputs only:

```text
25c107_summary.json
25c107_artifact_inventory.csv
25c107_column_key_risk_rows.csv
25c107_component_artifact_risk_summary.csv
25c107_decision_matrix.csv
25c107_blocker_matrix.csv
```

Required upstream status:

```text
25c107_summary.status = COREA_MEDIUM_SOT_PRECHECK_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

## Shortlist logic

Rank artifacts by component and role.

CoreA priority roles:

```text
corea_mapping_or_frozen;corea_source_or_selected
corea_source_or_selected
corea_mapping_or_frozen
```

MEDIUM priority roles:

```text
medium_final_sot;medium_source_or_selected
medium_arbitration;medium_source_or_selected
medium_arbitration
medium_source_or_selected
medium_arbitration;medium_final_sot
medium_mapping_or_frozen;medium_source_or_selected
```

Risk weights:

```text
hard_future_or_outcome key = 10
profit_or_representative key = 8
selection_or_arbitration key = 5
entry_time_candidate key = 1
role priority bonus = 0..100
```

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c108_corea_medium_replay_target_shortlist_audit_only
```

Output files:

```text
GOLD_V2_25C108_COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_AUDIT_ONLY_REPORT.md
25c108_summary.json
25c108_input_inventory.csv
25c108_replay_target_shortlist.csv
25c108_component_replay_scope.csv
25c108_target_column_risk_rows.csv
25c108_decision_matrix.csv
25c108_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c108_corea_medium_replay_target_shortlist_audit_only.zip
```

## Expected interpretation

CoreA target examples expected from 25C107:

```text
gold_v2_13b_corea_selected_source_rows.csv
gold_v2_13b_corea_source_cluster_ledger_normalized.csv
```

MEDIUM target examples expected from 25C107:

```text
gold_v2_13d2_tier2_final_sot_rows.csv
gold_v2_13d_medium_recomputed_final_rows.csv
gold_v2_13d_medium_selected_after_internal_priority.csv
gold_v2_13d_medium_blocked_by_high_arbitration.csv
gold_v2_13d_medium_dropped_by_internal_priority.csv
```

## Status names

If inputs are missing or upstream status fails:

```text
COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If both CoreA and MEDIUM replay targets are found:

```text
COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_READY_AUDIT_ONLY_LIVE_BLOCKED
```

If only one component has targets:

```text
COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_PARTIAL_AUDIT_ONLY_LIVE_BLOCKED
```

Even READY remains audit-only and live blocked.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not treat shortlist generation as replay proof.

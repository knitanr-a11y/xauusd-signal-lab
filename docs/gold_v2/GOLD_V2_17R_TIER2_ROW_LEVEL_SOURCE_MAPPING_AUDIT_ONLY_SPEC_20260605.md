# GOLD V2 17R TIER2 row-level source mapping audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY`
Mode: audit-only

## Purpose

17R audits whether the current MEDIUM full-set manifest contains row-level executable source identity for the TIER2_HVT component.

17R is source mapping / gap confirmation only. It does not implement predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17Q audited outputs and the already audited 17G manifest:

1. `FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only/gold_v2_17q_medium_full_set_component_parity_source_mapping_summary.json`
2. `FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only/gold_v2_17q_source_mapping_checks.csv`
3. `FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only/gold_v2_17q_component_source_mapping_matrix.csv`
4. `FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only/gold_v2_17q_source_artifact_requirements.csv`
5. `FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only/gold_v2_17q_required_next_gates.csv`
6. `FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only/gold_v2_17q_safety_matrix.csv`
7. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17Q must have status:

`MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 17Q state:

- source mapping ready true
- mapping rows 5
- predicate implementation allowed false
- executable parity implemented false
- dry-run execution false
- live evaluator false
- final signal false
- all external actions false

## TIER2 audit policy

17R must inspect the existing TIER2_HVT manifest identity row.

If the row is still a summary-chain reference rather than a row-level executable source identity, 17R must record:

`TIER2_ROW_LEVEL_SOURCE_IDENTITY_MISSING_CONFIRMED`

This is a valid audit completion state, but it remains a hard blocker for executable parity.

## Output folder

`FX_OUTPUTS/gold_v2_17r_tier2_row_level_source_mapping_audit_only`

## Main outputs

- `GOLD_V2_17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY_REPORT.md`
- `gold_v2_17r_tier2_row_level_source_mapping_summary.json`
- `gold_v2_17r_input_audit.csv`
- `gold_v2_17r_tier2_source_mapping_checks.csv`
- `gold_v2_17r_tier2_current_identity_rows.csv`
- `gold_v2_17r_tier2_required_source_artifacts.csv`
- `gold_v2_17r_required_next_gates.csv`
- `gold_v2_17r_blockers.csv`
- `gold_v2_17r_safety_matrix.csv`

## Success status

`TIER2_ROW_LEVEL_SOURCE_MAPPING_GAP_CONFIRMED_AUDIT_ONLY_LIVE_BLOCKED`

This means the TIER2 source mapping gap has been confirmed. It does not allow predicate implementation, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 17Q status is not expected,
- 17Q checks or safety contain STOP,
- TIER2_HVT manifest row count is not exactly 1,
- required manifest columns are missing,
- any output enables predicate/live/final/external actions.

## Recommended next step after success

After 17R success, the next possible step is:

`17S_RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY`

17S must remain source-mapping/audit-only and must not implement executable predicates.

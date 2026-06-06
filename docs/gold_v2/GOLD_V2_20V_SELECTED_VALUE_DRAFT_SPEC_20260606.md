# GOLD V2 20V selected human decision value draft spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20V_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20V records the explicitly selected human decision value as a draft-only audit artifact.

Selected value:

`REQUEST_MORE_AUDIT`

This value means the operator requests additional audit and does not approve source recovery.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_SELECTION_INTAKE_GATE_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20U must have STOP rows 0, and 20T/20U must not have recorded any prior value.

## Inputs

20U folder:

`FX_OUTPUTS/gold_v2_20u_tier2_source_identity_human_decision_value_selection_intake_gate_audit_only`

Required files:

- `gold_v2_20u_tier2_source_identity_human_decision_value_selection_intake_gate_summary.json`
- `gold_v2_20u_allowed_values.csv`
- `gold_v2_20u_intake_gate_checks.csv`
- `gold_v2_20u_required_next_gates.csv`
- `gold_v2_20u_safety_matrix.csv`
- `GOLD_V2_20U_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_SELECTION_INTAKE_GATE_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20V_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_audit_only`

Outputs:

- `GOLD_V2_20V_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_summary.json`
- `gold_v2_20v_input_audit.csv`
- `gold_v2_20v_selected_value_draft.json`
- `gold_v2_20v_draft_checks.csv`
- `gold_v2_20v_required_next_gates.csv`
- `gold_v2_20v_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`20W_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`

20V still blocks source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook.

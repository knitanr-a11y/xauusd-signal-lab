# GOLD V2 20T value entry readiness template spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20T_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20T prepares a value-entry readiness template after 20S passed.

20T does not record a decision value. The template keeps `decision_value=UNSET` and waits for a later explicit value selection.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20S must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20S folder:

`FX_OUTPUTS/gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_only`

Required files:

- `gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_summary.json`
- `gold_v2_20s_final_checks.csv`
- `gold_v2_20s_stage_status_audit.csv`
- `gold_v2_20s_required_next_gates.csv`
- `gold_v2_20s_safety_matrix.csv`
- `GOLD_V2_20S_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`

20O draft source:

- `FX_OUTPUTS/gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_audit_only/gold_v2_20o_execution_draft.json`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20T_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20t_tier2_source_identity_human_decision_value_entry_readiness_template_audit_only`

Outputs:

- `GOLD_V2_20T_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20t_tier2_source_identity_human_decision_value_entry_readiness_template_summary.json`
- `gold_v2_20t_input_audit.csv`
- `gold_v2_20t_value_entry_template.json`
- `gold_v2_20t_readiness_checks.csv`
- `gold_v2_20t_required_next_gates.csv`
- `gold_v2_20t_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`AWAIT_EXPLICIT_HUMAN_DECISION_VALUE_SELECTION`

20T still blocks source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook.

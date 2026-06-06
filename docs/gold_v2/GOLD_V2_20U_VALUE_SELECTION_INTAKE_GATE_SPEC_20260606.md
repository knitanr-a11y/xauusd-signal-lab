# GOLD V2 20U human decision value selection intake gate spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20U_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_SELECTION_INTAKE_GATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20U checks readiness for a later explicit human value selection.

20U does not select, infer, or record any decision value. It validates that 20T produced a still-UNSET template and that allowed values are present.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20T must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20T folder:

`FX_OUTPUTS/gold_v2_20t_tier2_source_identity_human_decision_value_entry_readiness_template_audit_only`

Required files:

- `gold_v2_20t_tier2_source_identity_human_decision_value_entry_readiness_template_summary.json`
- `gold_v2_20t_value_entry_template.json`
- `gold_v2_20t_readiness_checks.csv`
- `gold_v2_20t_required_next_gates.csv`
- `gold_v2_20t_safety_matrix.csv`
- `GOLD_V2_20T_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20U_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20u_tier2_source_identity_human_decision_value_selection_intake_gate_audit_only`

Outputs:

- `GOLD_V2_20U_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_SELECTION_INTAKE_GATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20u_tier2_source_identity_human_decision_value_selection_intake_gate_summary.json`
- `gold_v2_20u_input_audit.csv`
- `gold_v2_20u_intake_gate_checks.csv`
- `gold_v2_20u_allowed_values.csv`
- `gold_v2_20u_required_next_gates.csv`
- `gold_v2_20u_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_SELECTION_INTAKE_GATE_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`AWAIT_EXPLICIT_HUMAN_DECISION_VALUE_SELECTION`

20U still blocks source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook.

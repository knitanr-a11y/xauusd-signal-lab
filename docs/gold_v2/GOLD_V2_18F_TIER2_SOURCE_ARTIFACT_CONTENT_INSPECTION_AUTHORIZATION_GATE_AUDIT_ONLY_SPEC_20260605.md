# GOLD V2 18F TIER2 source artifact content inspection authorization gate audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18F_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

18F records the authorization gate required before any future TIER2 source artifact content inspection.

18F is an authorization gate only. It does not inspect candidate file contents, does not recover the TIER2 row-level source identity, does not reconstruct from OHLC, does not implement predicates, does not implement arbitration, does not evaluate OHLC, does not run replay, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

Unless a separate explicit approval file or command is provided, content inspection remains blocked.

## Source of truth

Use only audited 18E outputs:

1. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_tier2_source_artifact_content_inspection_plan_summary.json`
2. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_content_inspection_plan_checks.csv`
3. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_selected_priority_artifacts.csv`
4. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_content_inspection_plan.csv`
5. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_required_identity_validation_fields.csv`
6. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_stop_conditions.csv`
7. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_required_next_gates.csv`
8. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_blockers.csv`
9. `FX_OUTPUTS/gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only/gold_v2_18e_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer a recovered row-level identity.

## Expected input state

18E must have status:

`TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 18E state:

- content inspection plan ready true
- selected priority artifacts 13
- inspection plan rows 13
- content inspection allowed now false
- source recovery executed false
- implementation allowed false
- OHLC replay allowed false
- live enabled false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Authorization policy

18F must record these facts:

- content inspection is planned but not authorized,
- selected artifact count is carried forward,
- no content read is performed,
- no source recovery is performed,
- implementation/live/final/external actions remain disabled,
- a future execution step is blocked unless explicit approval is separately provided.

## Output folder

`FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only`

## Main outputs

- `GOLD_V2_18F_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_summary.json`
- `gold_v2_18f_input_audit.csv`
- `gold_v2_18f_authorization_gate_checks.csv`
- `gold_v2_18f_authorization_matrix.csv`
- `gold_v2_18f_blocked_execution_plan.csv`
- `gold_v2_18f_required_next_gates.csv`
- `gold_v2_18f_blockers.csv`
- `gold_v2_18f_safety_matrix.csv`

## Success status

`TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_READY_AUDIT_ONLY_CONTENT_INSPECTION_BLOCKED`

This means the gate is recorded. It does not mean content inspection is authorized or executed.

## Stop conditions

Stop if:

- any required input is missing,
- 18E status is not expected,
- 18E checks or safety contain STOP,
- content inspection was already allowed/executed,
- source recovery was already executed,
- any authorization row enables content inspection/source recovery/implementation/live/final/external actions without explicit approval,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18F success without explicit approval, the next state is:

`AWAIT_EXPLICIT_TIER2_CONTENT_INSPECTION_APPROVAL`

A future 18G content-inspection execution step must not be created unless explicit approval is provided separately.

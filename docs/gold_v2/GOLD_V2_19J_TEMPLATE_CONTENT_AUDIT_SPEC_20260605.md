# GOLD V2 19J actual human decision template content audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

19J content-audits the still-unset actual human decision template after 19I load-smoke passed.

19J is template-content-audit-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19J must not:

- promote the dry-run candidate identity ledger to source-of-truth
- execute source recovery
- finalize or recover source identity
- replay OHLC for source reconstruction
- enable live or final evaluator behavior
- send Discord or NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs
- call live hooks

## Upstream requirement

19J must stop unless 19I summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19J must also stop unless 19I template_load_smoke_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19I output folder:

`FX_OUTPUTS/gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only`

Required 19I inputs:

- `gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_summary.json`
- `gold_v2_19i_template_load_checks.csv`
- `gold_v2_19i_template_load_audit.csv`
- `gold_v2_19i_required_next_gates.csv`
- `gold_v2_19i_safety_matrix.csv`
- `GOLD_V2_19I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

19H template source:

- `gold_v2_19h_actual_decision_template.json`
- `gold_v2_19h_required_decision_fields.csv`
- `gold_v2_19h_allowed_decision_values.csv`

## Content checks

19J checks:

- 19I status is expected success
- 19I template_load_smoke_passed is true
- 19I total STOP rows is zero
- 19I decision_collected, decision_made, and approval_granted are false
- 19I load checks, template load audit, and safety matrix have zero STOP rows
- template_status is `TEMPLATE_ONLY_NOT_A_DECISION`
- decision_value and other human-entry fields remain `UNSET`
- evidence_acknowledged remains false
- approval and restricted execution flags remain false
- allowed decision values match the allowed value file
- required decision fields remain present
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_only`

Outputs:

- `GOLD_V2_19J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_summary.json`
- `gold_v2_19j_input_audit.csv`
- `gold_v2_19j_content_checks.csv`
- `gold_v2_19j_template_content_audit.csv`
- `gold_v2_19j_field_content_audit.csv`
- `gold_v2_19j_value_content_audit.csv`
- `gold_v2_19j_required_next_gates.csv`
- `gold_v2_19j_stop_conditions.csv`
- `gold_v2_19j_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the still-unset template content audited safely. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY`

19K may reconcile template preparation/load/content evidence. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

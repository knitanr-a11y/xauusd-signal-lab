# GOLD V2 18Z TIER2 source identity human decision intake content audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

18Z content-audits the unset human decision intake template and validation tables that passed 18Y load-smoke.

18Z is content-audit only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18Z must not:

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

18Z must stop unless 18Y summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18Z must also stop unless 18Y intake_load_smoke_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18Y output folder:

`FX_OUTPUTS/gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only`

Required 18Y inputs:

- `gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json`
- `gold_v2_18y_load_checks.csv`
- `gold_v2_18y_template_audit.csv`
- `gold_v2_18y_required_next_gates.csv`
- `gold_v2_18y_safety_matrix.csv`
- `GOLD_V2_18Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

18X output folder:

`FX_OUTPUTS/gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only`

Required 18X inputs:

- `gold_v2_18x_required_intake_fields.csv`
- `gold_v2_18x_allowed_decision_values.csv`
- `gold_v2_18x_human_decision_template.json`
- `gold_v2_18x_required_next_gates.csv`
- `gold_v2_18x_safety_matrix.csv`

Reference summaries from 18K through 18Y may be read for safety context only.

## Content-audit checks

18Z checks:

- 18Y status is expected success
- 18Y intake_load_smoke_passed is true
- 18Y total STOP rows is zero
- 18Y decision_collected, decision_made, and approval_granted are false
- 18Y load checks, template audit, and safety matrix have zero STOP rows
- required intake fields have unique names, expected required flags, and required type/requirement strings
- allowed decision values are unique, include non-approval values, and execute no action in 18X/18Z
- approval-candidate value is clearly not self-executing and still requires a later guarded step
- template remains unset and not a decision
- template restricted execution fields remain false
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only`

Outputs:

- `GOLD_V2_18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_summary.json`
- `gold_v2_18z_input_audit.csv`
- `gold_v2_18z_content_checks.csv`
- `gold_v2_18z_field_content_audit.csv`
- `gold_v2_18z_value_content_audit.csv`
- `gold_v2_18z_template_content_audit.csv`
- `gold_v2_18z_required_next_gates.csv`
- `gold_v2_18z_stop_conditions.csv`
- `gold_v2_18z_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the future human-decision intake template and validation table content passed audit-only checks. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY`

18AA may reconcile 18X/18Y/18Z intake evidence. 18AA must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

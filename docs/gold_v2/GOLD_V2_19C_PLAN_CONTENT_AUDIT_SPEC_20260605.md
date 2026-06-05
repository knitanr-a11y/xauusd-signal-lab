# GOLD V2 19C actual human decision intake plan content audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

19C content-audits the 19A actual human decision intake plan after 19B load-smoke passed.

19C is content-audit-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19C must not:

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

19C must stop unless 19B summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19C must also stop unless 19B plan_load_smoke_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19B output folder:

`FX_OUTPUTS/gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only`

Required 19B inputs:

- `gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_summary.json`
- `gold_v2_19b_load_checks.csv`
- `gold_v2_19b_plan_load_audit.csv`
- `gold_v2_19b_field_load_audit.csv`
- `gold_v2_19b_value_load_audit.csv`
- `gold_v2_19b_required_next_gates.csv`
- `gold_v2_19b_safety_matrix.csv`
- `GOLD_V2_19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

19A output folder:

`FX_OUTPUTS/gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only`

Required 19A content inputs:

- `gold_v2_19a_decision_intake_plan.md`
- `gold_v2_19a_required_decision_fields.csv`
- `gold_v2_19a_allowed_decision_values.csv`

## Content checks

19C checks:

- 19B status is expected success
- 19B plan_load_smoke_passed is true
- 19B total STOP rows is zero
- 19B decision_collected, decision_made, and approval_granted are false
- 19B load, plan, field, value, and safety audits have zero STOP rows
- plan text explicitly remains plan-only and not an actual decision
- plan text contains all required prohibitions
- future required fields include all required core fields with required=true
- allowed future decision values include the expected values and execute no actions
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_only`

Outputs:

- `GOLD_V2_19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_summary.json`
- `gold_v2_19c_input_audit.csv`
- `gold_v2_19c_content_checks.csv`
- `gold_v2_19c_plan_content_audit.csv`
- `gold_v2_19c_field_content_audit.csv`
- `gold_v2_19c_value_content_audit.csv`
- `gold_v2_19c_required_next_gates.csv`
- `gold_v2_19c_stop_conditions.csv`
- `gold_v2_19c_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the 19A decision-intake plan content was audited safely. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY`

19D may reconcile 19A/19B/19C plan evidence. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

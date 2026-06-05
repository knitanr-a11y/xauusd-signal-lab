# GOLD V2 19D actual human decision intake plan reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

19D reconciles the 19A decision-intake plan, the 19B load-smoke result, and the 19C content-audit result.

19D is reconciliation-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19D must not:

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

19D must stop unless 19C summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19D must also stop unless 19C plan_content_audit_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

Required folders:

- `FX_OUTPUTS/gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only`
- `FX_OUTPUTS/gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only`
- `FX_OUTPUTS/gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_only`

Required 19C inputs:

- `gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_summary.json`
- `gold_v2_19c_content_checks.csv`
- `gold_v2_19c_plan_content_audit.csv`
- `gold_v2_19c_field_content_audit.csv`
- `gold_v2_19c_value_content_audit.csv`
- `gold_v2_19c_required_next_gates.csv`
- `gold_v2_19c_safety_matrix.csv`
- `GOLD_V2_19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY_REPORT.md`

Required 19B and 19A evidence is used only for reconciliation.

## Reconciliation checks

19D checks:

- 19C status is expected success
- 19C plan_content_audit_passed is true
- 19C total STOP rows is zero
- 19A, 19B, and 19C all keep decision_collected false, decision_made false, and approval_granted false
- 19B and 19C check/safety tables have zero STOP rows
- 19A plan text length reconciles with 19B and 19C plan audit observations
- 19A required decision field count reconciles with 19B/19C field checks
- 19A allowed decision values reconcile with 19B/19C value checks
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19d_tier2_source_identity_human_decision_intake_actual_decision_plan_reconciliation_audit_only`

Outputs:

- `GOLD_V2_19D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_19d_tier2_source_identity_human_decision_intake_actual_decision_plan_reconciliation_summary.json`
- `gold_v2_19d_input_audit.csv`
- `gold_v2_19d_reconciliation_checks.csv`
- `gold_v2_19d_plan_reconciliation.csv`
- `gold_v2_19d_field_reconciliation.csv`
- `gold_v2_19d_value_reconciliation.csv`
- `gold_v2_19d_required_next_gates.csv`
- `gold_v2_19d_stop_conditions.csv`
- `gold_v2_19d_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the 19A/19B/19C decision-intake planning evidence reconciled safely. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_AUDIT_ONLY`

19E may review blockers after plan reconciliation. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

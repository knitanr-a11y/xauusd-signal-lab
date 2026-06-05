# GOLD V2 19B actual human decision intake plan load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

19B load-smokes the 19A actual human decision intake plan.

19B is load-smoke-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19B must not:

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

19B must stop unless 19A summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19B must also stop unless 19A decision_planning_ready is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19A output folder:

`FX_OUTPUTS/gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only`

Required 19A inputs:

- `gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_summary.json`
- `gold_v2_19a_planning_checks.csv`
- `gold_v2_19a_decision_intake_plan.md`
- `gold_v2_19a_required_decision_fields.csv`
- `gold_v2_19a_allowed_decision_values.csv`
- `gold_v2_19a_required_next_gates.csv`
- `gold_v2_19a_safety_matrix.csv`
- `GOLD_V2_19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY_REPORT.md`

## Load-smoke checks

19B checks:

- 19A status is expected success
- 19A decision_planning_ready is true
- 19A total STOP rows is zero
- 19A decision_collected, decision_made, and approval_granted are false
- 19A planning checks and safety matrix have zero STOP rows
- decision intake plan loads and explicitly remains plan-only, not an actual decision
- required decision fields load and include required core fields
- allowed decision values load and do not execute actions
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only`

Outputs:

- `GOLD_V2_19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_summary.json`
- `gold_v2_19b_input_audit.csv`
- `gold_v2_19b_load_checks.csv`
- `gold_v2_19b_plan_load_audit.csv`
- `gold_v2_19b_field_load_audit.csv`
- `gold_v2_19b_value_load_audit.csv`
- `gold_v2_19b_required_next_gates.csv`
- `gold_v2_19b_stop_conditions.csv`
- `gold_v2_19b_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the 19A decision-intake plan loaded safely. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY`

19C may content-audit the 19A plan. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

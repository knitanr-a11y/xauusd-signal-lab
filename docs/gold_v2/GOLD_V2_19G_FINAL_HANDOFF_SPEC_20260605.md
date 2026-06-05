# GOLD V2 19G actual human decision intake plan final handoff audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY`
Mode: audit-only

## Purpose

19G prepares a final audit-only handoff note for a later explicit actual human decision-intake workflow, using the 19F final audit-only summary.

19G is handoff-note-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19G must not:

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

19G must stop unless 19F summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19G must also stop unless 19F final_audit_ready is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19F output folder:

`FX_OUTPUTS/gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_only`

Required 19F inputs:

- `gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_summary.json`
- `gold_v2_19f_final_checks.csv`
- `gold_v2_19f_evidence_status.csv`
- `gold_v2_19f_blocker_final_status.csv`
- `gold_v2_19f_required_next_gates.csv`
- `gold_v2_19f_safety_matrix.csv`
- `GOLD_V2_19F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_ONLY_REPORT.md`

## Handoff checks

19G checks:

- 19F status is expected success
- 19F final_audit_ready is true
- 19F total STOP rows is zero
- 19F decision_collected, decision_made, and approval_granted are false
- 19F final checks, evidence status, blocker final status, and safety matrix have zero STOP rows
- handoff note explicitly says no actual decision, no approval, no source recovery, no finalization, no live/final enablement, no external actions, and NO_SIGNAL Discord disabled
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_audit_only`

Outputs:

- `GOLD_V2_19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`
- `gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_summary.json`
- `gold_v2_19g_input_audit.csv`
- `gold_v2_19g_handoff_checks.csv`
- `gold_v2_19g_final_handoff_note.md`
- `gold_v2_19g_required_next_gates.csv`
- `gold_v2_19g_stop_conditions.csv`
- `gold_v2_19g_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that a final audit-only handoff note is ready for a later explicit actual human decision-intake workflow. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY`

19H may prepare a still-unset actual decision template. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

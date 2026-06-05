# GOLD V2 19F actual human decision intake plan final audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_ONLY`
Mode: audit-only

## Purpose

19F prepares the final audit-only summary for the actual human decision intake plan after 19E blocker review passed.

19F is final-audit-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19F must not:

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

19F must stop unless 19E summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19F must also stop unless 19E blocker_review_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19E output folder:

`FX_OUTPUTS/gold_v2_19e_tier2_source_identity_human_decision_intake_actual_decision_plan_blocker_review_audit_only`

Required 19E inputs:

- `gold_v2_19e_tier2_source_identity_human_decision_intake_actual_decision_plan_blocker_review_summary.json`
- `gold_v2_19e_blocker_review_checks.csv`
- `gold_v2_19e_blockers_still_in_force.csv`
- `gold_v2_19e_required_next_gates.csv`
- `gold_v2_19e_safety_matrix.csv`
- `GOLD_V2_19E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md`

Reference summaries from 19A through 19E are read for evidence status only.

## Final audit checks

19F checks:

- 19E status is expected success
- 19E blocker_review_passed is true
- 19E total STOP rows is zero
- 19E decision_collected, decision_made, and approval_granted are false
- 19E blocker review and safety tables have zero STOP rows
- 19A through 19E summaries are present and successful
- blockers remain present, blocked, not script-clearable, and still in force
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_only`

Outputs:

- `GOLD_V2_19F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_ONLY_REPORT.md`
- `gold_v2_19f_tier2_source_identity_human_decision_intake_actual_decision_plan_final_audit_summary.json`
- `gold_v2_19f_input_audit.csv`
- `gold_v2_19f_final_checks.csv`
- `gold_v2_19f_evidence_status.csv`
- `gold_v2_19f_blocker_final_status.csv`
- `gold_v2_19f_required_next_gates.csv`
- `gold_v2_19f_stop_conditions.csv`
- `gold_v2_19f_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the actual human decision-intake plan final audit-only summary is ready. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY`

19G may prepare a final audit-only handoff note for a later explicit actual human decision-intake workflow. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

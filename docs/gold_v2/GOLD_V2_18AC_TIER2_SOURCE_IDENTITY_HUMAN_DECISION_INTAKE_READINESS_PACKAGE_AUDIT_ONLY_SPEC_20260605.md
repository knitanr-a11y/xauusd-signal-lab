# GOLD V2 18AC TIER2 source identity human decision intake readiness package audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AC packages the human-decision intake readiness evidence from 18X through 18AB.

18AC is readiness-package only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18AC must not:

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

18AC must stop unless 18AB summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AC must also stop unless 18AB blocker_review_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

Required folders:

- `FX_OUTPUTS/gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only`
- `FX_OUTPUTS/gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only`
- `FX_OUTPUTS/gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only`
- `FX_OUTPUTS/gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only`
- `FX_OUTPUTS/gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only`

Required 18AB inputs:

- `gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_summary.json`
- `gold_v2_18ab_blocker_review_checks.csv`
- `gold_v2_18ab_blockers_still_in_force.csv`
- `gold_v2_18ab_required_next_gates.csv`
- `gold_v2_18ab_safety_matrix.csv`
- `GOLD_V2_18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md`

Required intake evidence inputs from 18X through 18AA are summarized into an index and are not used to perform any decision or approval.

## Package checks

18AC checks:

- 18AB status is expected success
- 18AB blocker_review_passed is true
- 18AB total STOP rows is zero
- 18AB decision_collected, decision_made, and approval_granted are false
- required evidence files from 18X through 18AB are present
- all included check/safety tables have zero STOP rows
- blockers still in force are present and not clearable by script
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only`

Outputs:

- `GOLD_V2_18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md`
- `gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_summary.json`
- `gold_v2_18ac_input_audit.csv`
- `gold_v2_18ac_package_checks.csv`
- `gold_v2_18ac_evidence_package_index.csv`
- `gold_v2_18ac_blocker_package_summary.csv`
- `gold_v2_18ac_required_next_gates.csv`
- `gold_v2_18ac_stop_conditions.csv`
- `gold_v2_18ac_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that human-decision intake readiness evidence was packaged. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY`

18AD may load-smoke the 18AC readiness package. 18AD must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

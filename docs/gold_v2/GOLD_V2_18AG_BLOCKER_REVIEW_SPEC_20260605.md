# GOLD V2 18AG readiness package blocker review audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AG reviews the blockers that must remain in force after the 18AF readiness-package reconciliation passed.

18AG is blocker-review only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

18AG must not:

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

18AG must stop unless 18AF summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AG must also stop unless 18AF package_reconciliation_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

18AF output folder:

`FX_OUTPUTS/gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_audit_only`

Required 18AF inputs:

- `gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_summary.json`
- `gold_v2_18af_reconciliation_checks.csv`
- `gold_v2_18af_required_next_gates.csv`
- `gold_v2_18af_safety_matrix.csv`
- `GOLD_V2_18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY_REPORT.md`

18AB/18AC evidence inputs:

- `gold_v2_18ab_blockers_still_in_force.csv`
- `gold_v2_18ac_blocker_package_summary.csv`

## Blocker review checks

18AG checks:

- 18AF status is expected success
- 18AF package_reconciliation_passed is true
- 18AF total STOP rows is zero
- 18AF decision_collected, decision_made, and approval_granted are false
- 18AF reconciliation and safety tables have zero STOP rows
- blockers still in force are present
- every blocker remains blocked and must remain blocked before human intake
- scripts cannot clear blockers
- blocker package summary still reports blockers present, blocked, not script-clearable, and template UNSET
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_audit_only`

Outputs:

- `GOLD_V2_18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md`
- `gold_v2_18ag_tier2_source_identity_human_decision_intake_readiness_package_blocker_review_summary.json`
- `gold_v2_18ag_input_audit.csv`
- `gold_v2_18ag_blocker_review_checks.csv`
- `gold_v2_18ag_blockers_still_in_force.csv`
- `gold_v2_18ag_required_next_gates.csv`
- `gold_v2_18ag_stop_conditions.csv`
- `gold_v2_18ag_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Required next gate

`18AH_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_FINAL_AUDIT_ONLY`

18AH may prepare a final audit-only readiness package summary. It must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

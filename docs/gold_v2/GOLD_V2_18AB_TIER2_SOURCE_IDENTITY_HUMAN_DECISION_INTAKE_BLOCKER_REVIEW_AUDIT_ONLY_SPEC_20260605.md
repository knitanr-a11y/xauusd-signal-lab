# GOLD V2 18AB TIER2 source identity human decision intake blocker review audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AB reviews the blockers that must remain in force before any later human decision intake.

18AB is blocker-review only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18AB must not:

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

18AB must stop unless 18AA summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AB must also stop unless 18AA intake_reconciliation_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18AA output folder:

`FX_OUTPUTS/gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only`

Required 18AA inputs:

- `gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_summary.json`
- `gold_v2_18aa_reconciliation_checks.csv`
- `gold_v2_18aa_required_next_gates.csv`
- `gold_v2_18aa_safety_matrix.csv`
- `GOLD_V2_18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY_REPORT.md`

18V output folder:

`FX_OUTPUTS/gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only`

Required 18V inputs:

- `gold_v2_18v_remaining_blockers.csv`
- `gold_v2_18v_manual_decision_summary.csv`

18X output folder:

`FX_OUTPUTS/gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only`

Required 18X inputs:

- `gold_v2_18x_allowed_decision_values.csv`
- `gold_v2_18x_human_decision_template.json`

Reference summaries from 18K through 18AA may be read for safety context only.

## Blocker review checks

18AB checks:

- 18AA status is expected success
- 18AA intake_reconciliation_passed is true
- 18AA total STOP rows is zero
- 18AA decision_collected, decision_made, and approval_granted are false
- 18AA checks and safety matrix have zero STOP rows
- remaining blockers are present and all still blocking
- scripts cannot clear blockers
- source recovery/finalization/live/final signal/external action blockers are present
- decision values still execute no action
- template remains unset and not a decision
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_audit_only`

Outputs:

- `GOLD_V2_18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md`
- `gold_v2_18ab_tier2_source_identity_human_decision_intake_blocker_review_summary.json`
- `gold_v2_18ab_input_audit.csv`
- `gold_v2_18ab_blocker_review_checks.csv`
- `gold_v2_18ab_blockers_still_in_force.csv`
- `gold_v2_18ab_required_next_gates.csv`
- `gold_v2_18ab_stop_conditions.csv`
- `gold_v2_18ab_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that blockers were reviewed and remain in force. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY`

18AC may package 18X through 18AB intake readiness evidence. 18AC must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

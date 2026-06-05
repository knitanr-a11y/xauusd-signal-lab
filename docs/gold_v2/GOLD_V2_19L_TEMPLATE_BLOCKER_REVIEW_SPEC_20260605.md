# GOLD V2 19L actual human decision template blocker review audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY`
Mode: audit-only

## Purpose

19L reviews that all blocked actions still remain blocked after the 19K actual decision template reconciliation passed.

19L is blocker-review-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19L must not:

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

19L must stop unless 19K summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19L must also stop unless 19K template_reconciliation_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19K output folder:

`FX_OUTPUTS/gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_audit_only`

Required 19K inputs:

- `gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_summary.json`
- `gold_v2_19k_reconciliation_checks.csv`
- `gold_v2_19k_required_next_gates.csv`
- `gold_v2_19k_safety_matrix.csv`
- `GOLD_V2_19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY_REPORT.md`

19E blocker evidence is used as the current source for blocked actions:

- `gold_v2_19e_blockers_still_in_force.csv`

## Blocker review checks

19L checks:

- 19K status is expected success
- 19K template_reconciliation_passed is true
- 19K total STOP rows is zero
- 19K decision_collected, decision_made, and approval_granted are false
- 19K reconciliation and safety tables have zero STOP rows
- blockers still in force are present
- every blocker remains BLOCKED
- no blocker is script-clearable
- every blocker remains still in force after 19E and after 19L
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_audit_only`

Outputs:

- `GOLD_V2_19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md`
- `gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_summary.json`
- `gold_v2_19l_input_audit.csv`
- `gold_v2_19l_blocker_review_checks.csv`
- `gold_v2_19l_blockers_still_in_force.csv`
- `gold_v2_19l_required_next_gates.csv`
- `gold_v2_19l_stop_conditions.csv`
- `gold_v2_19l_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that blockers remain in force after 19K. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY`

19M may prepare a final audit-only summary for the still-unset actual decision template. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

# GOLD V2 19K actual human decision template reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

19K reconciles the 19H template preparation result, the 19I template load-smoke result, and the 19J template content-audit result.

19K is reconciliation-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19K must not:

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

19K must stop unless 19J summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19K must also stop unless 19J template_content_audit_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

Required folders:

- `FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only`
- `FX_OUTPUTS/gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only`
- `FX_OUTPUTS/gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_only`

Required 19J inputs:

- `gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_summary.json`
- `gold_v2_19j_content_checks.csv`
- `gold_v2_19j_template_content_audit.csv`
- `gold_v2_19j_field_content_audit.csv`
- `gold_v2_19j_value_content_audit.csv`
- `gold_v2_19j_required_next_gates.csv`
- `gold_v2_19j_safety_matrix.csv`
- `GOLD_V2_19J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY_REPORT.md`

Required 19I and 19H evidence is used only for reconciliation.

## Reconciliation checks

19K checks:

- 19J status is expected success
- 19J template_content_audit_passed is true
- 19J total STOP rows is zero
- 19H, 19I, and 19J all keep decision_collected false, decision_made false, and approval_granted false
- 19I and 19J check/safety tables have zero STOP rows
- 19H template status reconciles with 19I and 19J observations
- 19H template decision_value reconciles with 19I and 19J observations as `UNSET`
- 19H required fields reconcile with 19I/19J field checks
- 19H allowed decision values reconcile with 19I/19J value checks
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_audit_only`

Outputs:

- `GOLD_V2_19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_summary.json`
- `gold_v2_19k_input_audit.csv`
- `gold_v2_19k_reconciliation_checks.csv`
- `gold_v2_19k_template_reconciliation.csv`
- `gold_v2_19k_field_reconciliation.csv`
- `gold_v2_19k_value_reconciliation.csv`
- `gold_v2_19k_required_next_gates.csv`
- `gold_v2_19k_stop_conditions.csv`
- `gold_v2_19k_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the still-unset template evidence reconciled safely. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY`

19L may review blockers after template reconciliation. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

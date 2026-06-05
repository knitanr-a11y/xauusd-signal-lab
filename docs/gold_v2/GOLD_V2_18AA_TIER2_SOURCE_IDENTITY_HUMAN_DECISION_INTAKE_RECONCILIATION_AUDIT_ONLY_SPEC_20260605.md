# GOLD V2 18AA TIER2 source identity human decision intake reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AA reconciles the human-decision intake planning evidence produced by 18X, load-smoked by 18Y, and content-audited by 18Z.

18AA is reconciliation-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18AA must not:

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

18AA must stop unless 18Z summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AA must also stop unless 18Z intake_content_audit_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18X output folder:

`FX_OUTPUTS/gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only`

18Y output folder:

`FX_OUTPUTS/gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only`

18Z output folder:

`FX_OUTPUTS/gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only`

Required 18Z inputs:

- `gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_summary.json`
- `gold_v2_18z_content_checks.csv`
- `gold_v2_18z_field_content_audit.csv`
- `gold_v2_18z_value_content_audit.csv`
- `gold_v2_18z_template_content_audit.csv`
- `gold_v2_18z_required_next_gates.csv`
- `gold_v2_18z_safety_matrix.csv`
- `GOLD_V2_18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY_REPORT.md`

Required 18Y inputs:

- `gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json`
- `gold_v2_18y_load_checks.csv`
- `gold_v2_18y_template_audit.csv`
- `gold_v2_18y_required_next_gates.csv`
- `gold_v2_18y_safety_matrix.csv`

Required 18X inputs:

- `gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json`
- `gold_v2_18x_required_intake_fields.csv`
- `gold_v2_18x_allowed_decision_values.csv`
- `gold_v2_18x_human_decision_template.json`
- `gold_v2_18x_required_next_gates.csv`
- `gold_v2_18x_safety_matrix.csv`

Reference summaries from 18K through 18Z may be read for safety context only.

## Reconciliation checks

18AA checks:

- 18Z status is expected success
- 18Z intake_content_audit_passed is true
- 18Z total STOP rows is zero
- 18X, 18Y, and 18Z all keep decision_collected false, decision_made false, and approval_granted false
- 18Y and 18Z check tables have zero STOP rows
- 18X required field count reconciles with 18Y and 18Z field checks
- 18X allowed decision value count reconciles with 18Y and 18Z value checks
- 18X template unset status reconciles with 18Y template audit and 18Z template content audit
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only`

Outputs:

- `GOLD_V2_18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_summary.json`
- `gold_v2_18aa_input_audit.csv`
- `gold_v2_18aa_reconciliation_checks.csv`
- `gold_v2_18aa_field_count_reconciliation.csv`
- `gold_v2_18aa_value_count_reconciliation.csv`
- `gold_v2_18aa_template_state_reconciliation.csv`
- `gold_v2_18aa_required_next_gates.csv`
- `gold_v2_18aa_stop_conditions.csv`
- `gold_v2_18aa_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the 18X/18Y/18Z intake evidence reconciled. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY`

18AB may summarize the blockers that must remain in force before any later human decision intake. 18AB must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

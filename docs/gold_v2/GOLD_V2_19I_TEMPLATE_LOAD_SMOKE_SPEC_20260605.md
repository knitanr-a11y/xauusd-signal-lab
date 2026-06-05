# GOLD V2 19I actual human decision template load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

19I load-smokes the still-unset actual human decision template prepared by 19H.

19I is template-load-smoke-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19I must not:

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

19I must stop unless 19H summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19I must also stop unless 19H template_prepared is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19H output folder:

`FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only`

Required 19H inputs:

- `gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_summary.json`
- `gold_v2_19h_template_checks.csv`
- `gold_v2_19h_actual_decision_template.json`
- `gold_v2_19h_required_decision_fields.csv`
- `gold_v2_19h_allowed_decision_values.csv`
- `gold_v2_19h_required_next_gates.csv`
- `gold_v2_19h_safety_matrix.csv`
- `GOLD_V2_19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY_REPORT.md`

## Load-smoke checks

19I checks:

- 19H status is expected success
- 19H template_prepared is true
- 19H total STOP rows is zero
- 19H decision_collected, decision_made, and approval_granted are false
- 19H template checks and safety matrix have zero STOP rows
- template JSON loads
- template status remains `TEMPLATE_ONLY_NOT_A_DECISION`
- decision_value remains `UNSET`
- decision fields remain unset or false as expected
- restricted template execution flags remain false
- required fields and allowed values load
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only`

Outputs:

- `GOLD_V2_19I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_summary.json`
- `gold_v2_19i_input_audit.csv`
- `gold_v2_19i_template_load_checks.csv`
- `gold_v2_19i_template_load_audit.csv`
- `gold_v2_19i_required_next_gates.csv`
- `gold_v2_19i_stop_conditions.csv`
- `gold_v2_19i_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the still-unset template loaded safely. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY`

19J may content-audit the still-unset template. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

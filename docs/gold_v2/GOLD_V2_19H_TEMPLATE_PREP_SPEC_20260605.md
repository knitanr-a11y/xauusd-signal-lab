# GOLD V2 19H actual human decision template preparation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

19H prepares a still-unset actual human decision template for a later explicit decision-intake workflow.

19H is template-preparation-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19H must not:

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

19H must stop unless 19G summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19H must also stop unless 19G handoff_ready is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19G output folder:

`FX_OUTPUTS/gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_audit_only`

Required 19G inputs:

- `gold_v2_19g_tier2_source_identity_human_decision_intake_actual_decision_plan_final_handoff_summary.json`
- `gold_v2_19g_handoff_checks.csv`
- `gold_v2_19g_final_handoff_note.md`
- `gold_v2_19g_required_next_gates.csv`
- `gold_v2_19g_safety_matrix.csv`
- `GOLD_V2_19G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`

19A plan artifacts are used only to construct the still-unset template shape:

- `gold_v2_19a_required_decision_fields.csv`
- `gold_v2_19a_allowed_decision_values.csv`

## Template preparation checks

19H checks:

- 19G status is expected success
- 19G handoff_ready is true
- 19G total STOP rows is zero
- 19G decision_collected, decision_made, and approval_granted are false
- 19G handoff checks and safety matrix have zero STOP rows
- required decision fields load
- allowed decision values load
- generated template decision_value remains `UNSET`
- generated template approval_granted remains false
- generated template source_recovery_requested remains false
- generated template source_recovery_allowed remains false
- generated template source_identity_finalization_allowed remains false
- generated template is marked `TEMPLATE_ONLY_NOT_A_DECISION`
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only`

Outputs:

- `GOLD_V2_19H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_summary.json`
- `gold_v2_19h_input_audit.csv`
- `gold_v2_19h_template_checks.csv`
- `gold_v2_19h_actual_decision_template.json`
- `gold_v2_19h_required_decision_fields.csv`
- `gold_v2_19h_allowed_decision_values.csv`
- `gold_v2_19h_required_next_gates.csv`
- `gold_v2_19h_stop_conditions.csv`
- `gold_v2_19h_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that a still-unset actual human decision template is prepared. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_LOAD_SMOKE_AUDIT_ONLY`

19I may load-smoke the still-unset template. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

# GOLD V2 19A actual human decision intake planning audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY`
Mode: audit-only

## Purpose

19A plans how a later explicit human decision could be collected, validated, and audited.

19A is planning-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19A must not:

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

19A must stop unless 18AI summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19A must also stop unless 18AI handoff_ready is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

18AI output folder:

`FX_OUTPUTS/gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_audit_only`

Required 18AI inputs:

- `gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_summary.json`
- `gold_v2_18ai_handoff_checks.csv`
- `gold_v2_18ai_handoff_note.md`
- `gold_v2_18ai_required_next_gates.csv`
- `gold_v2_18ai_safety_matrix.csv`
- `GOLD_V2_18AI_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`

18X input definitions are used only as planning references:

- `gold_v2_18x_required_intake_fields.csv`
- `gold_v2_18x_allowed_decision_values.csv`
- `gold_v2_18x_human_decision_template.json`

## Planning checks

19A checks:

- 18AI status is expected success
- 18AI handoff_ready is true
- 18AI total STOP rows is zero
- 18AI decision_collected, decision_made, and approval_granted are false
- 18AI handoff checks and safety matrix have zero STOP rows
- required decision fields are available for a future intake plan
- allowed decision values are available for a future intake plan
- current template remains unset and not a decision
- the generated plan is explicitly plan-only, not an actual decision
- source recovery, source identity finalization, live, and final signal remain blocked by next gates

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only`

Outputs:

- `GOLD_V2_19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY_REPORT.md`
- `gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_summary.json`
- `gold_v2_19a_input_audit.csv`
- `gold_v2_19a_planning_checks.csv`
- `gold_v2_19a_decision_intake_plan.md`
- `gold_v2_19a_required_decision_fields.csv`
- `gold_v2_19a_allowed_decision_values.csv`
- `gold_v2_19a_required_next_gates.csv`
- `gold_v2_19a_stop_conditions.csv`
- `gold_v2_19a_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that a later actual human-decision intake process has an audit-only plan. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY`

19B may load-smoke the 19A plan. It must still not collect a decision, execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

# GOLD V2 18X TIER2 source identity human decision intake planning audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY`
Mode: audit-only

## Purpose

18X plans how a later explicit human decision should be received and validated after 18W decision packet preparation passed.

18X is intake-planning only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18X must not:

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

18X must stop unless 18W summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18X must also stop unless 18W decision_packet_prepared is true, total STOP rows are zero, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18W output folder:

`FX_OUTPUTS/gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only`

Required 18W inputs:

- `gold_v2_18w_tier2_source_identity_human_review_decision_packet_summary.json`
- `gold_v2_18w_decision_packet_checks.csv`
- `gold_v2_18w_human_decision_options.csv`
- `gold_v2_18w_decision_packet_markdown.md`
- `gold_v2_18w_required_next_gates.csv`
- `gold_v2_18w_safety_matrix.csv`
- `GOLD_V2_18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY_REPORT.md`

18V output folder:

`FX_OUTPUTS/gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only`

Required 18V inputs:

- `gold_v2_18v_remaining_blockers.csv`
- `gold_v2_18v_manual_decision_summary.csv`

Reference summaries from 18K through 18W may be read for safety context only.

## Planning checks

18X checks:

- 18W status is expected success
- 18W decision_packet_prepared is true
- 18W total STOP rows is zero
- 18W decision_made and approval_granted are false
- 18W decision packet checks and safety matrix have zero STOP rows
- 18W human decision options exist and are HUMAN_ONLY
- all human decision options have script_executes_action false
- 18V blockers remain present and still blocking
- required intake fields are defined
- allowed intake decision values are defined
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only`

Outputs:

- `GOLD_V2_18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY_REPORT.md`
- `gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json`
- `gold_v2_18x_input_audit.csv`
- `gold_v2_18x_intake_planning_checks.csv`
- `gold_v2_18x_required_intake_fields.csv`
- `gold_v2_18x_allowed_decision_values.csv`
- `gold_v2_18x_human_decision_template.json`
- `gold_v2_18x_required_next_gates.csv`
- `gold_v2_18x_stop_conditions.csv`
- `gold_v2_18x_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that a future human-decision intake plan was prepared. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY`

18Y may load-smoke the planned intake template and validation tables. 18Y must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

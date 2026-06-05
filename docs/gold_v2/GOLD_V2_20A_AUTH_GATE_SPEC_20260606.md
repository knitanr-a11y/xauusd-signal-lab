# GOLD V2 20A actual decision intake authorization gate audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20A records and audits the explicit human authorization to proceed from 19N into the actual decision intake audit-only preparation path.

20A is authorization-gate-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

The authorization scope is limited to preparing the next actual decision intake audit-only step. It does not authorize source recovery, source identity finalization, Discord, MT5, AI API, live hook, live evaluator, or final signal.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

20A must not:

- collect or infer an actual decision value
- promote the dry-run candidate identity ledger to source-of-truth
- execute source recovery
- finalize or recover source identity
- replay OHLC for source reconstruction
- enable live evaluator, live hook, or final signal behavior
- send Discord or NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs
- make any MT5/Discord/live-side external action

## Upstream requirement

20A must stop unless 19N summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20A must also stop unless 19N handoff_ready is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Human authorization statement

This implementation records the current chat instruction as an audit-only authorization to continue into the next actual decision intake preparation gate.

Recorded authorization text:

`USER_AUTHORIZED_PROCEED_AFTER_19N_TO_ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION`

Allowed scope:

`ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY`

Still blocked:

- actual decision collection
- approval
- source recovery
- source identity finalization or recovery
- source-of-truth promotion
- live evaluator
- final signal
- Discord send
- NO_SIGNAL Discord send
- MT5 order
- AI API
- live hook

## Inputs

19N input folder:

`FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only`

Required 19N inputs:

- `gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_summary.json`
- `gold_v2_19n_handoff_checks.csv`
- `gold_v2_19n_final_handoff_note.md`
- `gold_v2_19n_required_next_gates.csv`
- `gold_v2_19n_safety_matrix.csv`
- `GOLD_V2_19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`

## Trade/strategy fields

20A does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Audit method

20A audits:

- 19N status equals the expected success status
- 19N handoff_ready is true
- 19N total_stop_rows is zero
- 19N did not collect a decision, make a decision, or grant approval
- 19N handoff checks and safety matrix have zero STOP rows
- 19N next gate allows only the manual authorization checkpoint and keeps forbidden gates blocked
- forbidden summary flags remain false
- 20A authorization record scope is audit-only preparation only
- 20A authorization record does not permit actual decision collection or any restricted external action

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only`

Outputs:

- `GOLD_V2_20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_summary.json`
- `gold_v2_20a_input_audit.csv`
- `gold_v2_20a_authorization_record.csv`
- `gold_v2_20a_authorization_checks.csv`
- `gold_v2_20a_required_next_gates.csv`
- `gold_v2_20a_stop_conditions.csv`
- `gold_v2_20a_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the user authorized moving from the 19N handoff into a later actual decision intake audit-only preparation step. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20A_AUTH_GATE.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20a_auth_gate.py
pause
```

## Success conditions

20A succeeds only when all authorization checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY`

## Stop conditions

20A must stop when any required input is missing, upstream 19N did not pass, any decision/approval flag is true, any upstream STOP row exists, any forbidden gate is allowed, any restricted external-action flag is true, or the authorization scope is broader than audit-only preparation.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20A_AUTH_GATE_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20a_auth_gate.py`
- BAT: `scripts/gold_v2_runtime/bat/20A_AUTH_GATE.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only/GOLD_V2_20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_summary.json`
- `FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only/gold_v2_20a_authorization_record.csv`
- `FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only/gold_v2_20a_authorization_checks.csv`
- `FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only/gold_v2_20a_safety_matrix.csv`

## Do not run

Do not run source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

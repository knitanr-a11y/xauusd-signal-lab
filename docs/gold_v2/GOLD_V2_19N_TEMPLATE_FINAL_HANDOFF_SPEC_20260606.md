# GOLD V2 19N actual human decision template final handoff audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY`
Mode: audit-only

## Purpose

19N prepares a final audit-only handoff note for the still-unset actual human decision template after 19M final audit passed.

19N is handoff-note-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19N must not:

- promote the dry-run candidate identity ledger to source-of-truth
- execute source recovery
- finalize or recover source identity
- replay OHLC for source reconstruction
- enable live evaluator, live hook, or final signal behavior
- send Discord or NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs
- make any MT5/Discord/live-side external action
- collect or infer an actual human decision

## Upstream requirement

19N must stop unless 19M summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19N must also stop unless 19M final_audit_ready is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19M input folder:

`FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only`

Required 19M inputs:

- `gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_summary.json`
- `gold_v2_19m_final_checks.csv`
- `gold_v2_19m_evidence_status.csv`
- `gold_v2_19m_blocker_final_status.csv`
- `gold_v2_19m_required_next_gates.csv`
- `gold_v2_19m_safety_matrix.csv`
- `GOLD_V2_19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY_REPORT.md`

## Trade/strategy fields

19N does not evaluate trades and does not read OHLC or trade ledgers.

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

19N audits:

- 19M status equals the expected success status
- 19M final_audit_ready is true
- 19M total_stop_rows is zero
- 19M did not collect a decision, make a decision, or grant approval
- 19M final checks, evidence status, blocker status, and safety matrix have zero STOP rows
- forbidden next gates remain disallowed
- forbidden summary flags remain false
- the generated 19N handoff note contains explicit retained prohibitions
- the generated 19N handoff note says future actual decision intake requires explicit human authorization

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only`

Outputs:

- `GOLD_V2_19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`
- `gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_summary.json`
- `gold_v2_19n_input_audit.csv`
- `gold_v2_19n_handoff_checks.csv`
- `gold_v2_19n_final_handoff_note.md`
- `gold_v2_19n_required_next_gates.csv`
- `gold_v2_19n_stop_conditions.csv`
- `gold_v2_19n_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the still-unset template has a final audit-only handoff note. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\19N_TEMPLATE_FINAL_HANDOFF.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_19n_template_final_handoff.py
pause
```

## Success conditions

19N succeeds only when all handoff checks are PASS and `total_stop_rows` is 0.

After a successful 19N, the next state is not automatic execution. The next state is:

`AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_INTAKE`

## Stop conditions

19N must stop when any required input is missing, upstream 19M did not pass, any decision/approval flag is true, any upstream STOP row exists, any forbidden gate is allowed, any restricted external-action flag is true, or the handoff note does not explicitly retain all prohibitions.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_19N_TEMPLATE_FINAL_HANDOFF_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_19n_template_final_handoff.py`
- BAT: `scripts/gold_v2_runtime/bat/19N_TEMPLATE_FINAL_HANDOFF.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only/GOLD_V2_19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_summary.json`
- `FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only/gold_v2_19n_handoff_checks.csv`
- `FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only/gold_v2_19n_final_handoff_note.md`
- `FX_OUTPUTS/gold_v2_19n_tier2_source_identity_human_decision_intake_actual_decision_template_final_handoff_audit_only/gold_v2_19n_safety_matrix.csv`

## Do not run

Do not run source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

# GOLD V2 19M actual human decision template final audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY`
Mode: audit-only

## Purpose

19M prepares the final audit-only summary for the still-unset actual human decision template after 19L passed blocker review.

19M is final-audit-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

19M must not:

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

19M must stop unless 19L summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

19M must also stop unless 19L blocker_review_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

19M uses only audited 19H-19L artifacts under `FX_OUTPUTS`.

Primary 19L input folder:

`FX_OUTPUTS/gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_audit_only`

Required 19L inputs:

- `gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_summary.json`
- `gold_v2_19l_blocker_review_checks.csv`
- `gold_v2_19l_blockers_still_in_force.csv`
- `gold_v2_19l_required_next_gates.csv`
- `gold_v2_19l_safety_matrix.csv`
- `GOLD_V2_19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md`

Template source input:

`FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only/gold_v2_19h_actual_decision_template.json`

Evidence folders checked:

- `gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only`
- `gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only`
- `gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_only`
- `gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_audit_only`
- `gold_v2_19l_tier2_source_identity_human_decision_intake_actual_decision_template_blocker_review_audit_only`

## Trade/strategy fields

19M does not evaluate trades and does not read OHLC or trade ledgers.

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

19M audits:

- 19L status equals the expected success status
- 19L blocker_review_passed is true
- 19L total_stop_rows is zero
- 19H-19L summaries all report their expected success flags and zero STOP rows
- 19H-19L summaries did not collect a decision, make a decision, or grant approval
- 19L blocker rows are present
- every blocker remains `BLOCKED`
- every blocker remains `script_can_clear=False`
- every blocker remains `still_in_force_after_19l=True`
- the actual decision template remains `TEMPLATE_ONLY_NOT_A_DECISION`
- the actual decision template `decision_value` and other human-input fields remain `UNSET`
- restricted template flags remain false
- forbidden next gates are not allowed
- forbidden summary flags remain false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only`

Outputs:

- `GOLD_V2_19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY_REPORT.md`
- `gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_summary.json`
- `gold_v2_19m_input_audit.csv`
- `gold_v2_19m_final_checks.csv`
- `gold_v2_19m_evidence_status.csv`
- `gold_v2_19m_blocker_final_status.csv`
- `gold_v2_19m_required_next_gates.csv`
- `gold_v2_19m_stop_conditions.csv`
- `gold_v2_19m_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the still-unset template is ready for a final audit-only handoff. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\19M_TEMPLATE_FINAL_AUDIT.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_19m_template_final_audit.py
pause
```

## Success conditions

19M succeeds only when all final checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`19N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_HANDOFF_AUDIT_ONLY`

## Stop conditions

19M must stop when any required input is missing, upstream 19L did not pass, the template no longer remains unset, any blocker can be cleared by script, any blocker is no longer blocked/still in force, any decision/approval flag is true, any forbidden gate is allowed, or any restricted external-action flag is true.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_19M_TEMPLATE_FINAL_AUDIT_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_19m_template_final_audit.py`
- BAT: `scripts/gold_v2_runtime/bat/19M_TEMPLATE_FINAL_AUDIT.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only/GOLD_V2_19M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_FINAL_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_summary.json`
- `FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only/gold_v2_19m_final_checks.csv`
- `FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only/gold_v2_19m_blocker_final_status.csv`
- `FX_OUTPUTS/gold_v2_19m_tier2_source_identity_human_decision_intake_actual_decision_template_final_audit_only/gold_v2_19m_safety_matrix.csv`

## Do not run

Do not run source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

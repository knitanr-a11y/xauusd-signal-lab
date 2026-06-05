# GOLD V2 20D actual decision intake draft content audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20D content-audits the unset actual decision intake draft package that passed the 20C load-smoke.

20D is content-audit-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

20D focuses on semantic/content integrity: the draft must remain a non-decision, all human-entered fields must remain unset, allowed values must be present but no-action, and the required human intake fields must be complete before any later actual decision collection is separately authorized.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

20D must not:

- collect or infer an actual decision value
- approve source recovery or any other action
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

20D must stop unless 20C summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20D must also stop unless 20C draft_load_smoke_passed is true, total STOP rows are zero, draft_status is `DRAFT_ONLY_NOT_A_DECISION`, decision_value is `UNSET`, actual_decision_collection_allowed is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20C input folder:

`FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only`

Required 20C inputs:

- `gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json`
- `gold_v2_20c_draft_load_audit.csv`
- `gold_v2_20c_load_checks.csv`
- `gold_v2_20c_required_next_gates.csv`
- `gold_v2_20c_safety_matrix.csv`
- `GOLD_V2_20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

20B draft source inputs:

- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_decision_intake_draft.json`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_required_decision_fields.csv`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_allowed_decision_values.csv`

## Trade/strategy fields

20D does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Content audit checks

20D checks:

- draft JSON still has `draft_status = DRAFT_ONLY_NOT_A_DECISION`
- draft decision fields remain `UNSET`
- evidence acknowledgement remains false
- approval and actual decision collection remain false
- all restricted action flags remain false
- required decision field definitions contain the expected required fields
- allowed decision values contain required values while still executing no action
- no duplicate required fields or allowed values exist
- upstream 20C load checks, draft-load audit, and safety matrix have zero STOP rows
- forbidden next gates remain blocked

## Expected required field names

20D expects the field definition source to include at least:

- `decision_id`
- `decision_timestamp_utc`
- `decision_value`
- `human_reviewer`
- `evidence_acknowledged`
- `explicit_phrase`

## Expected allowed decision values

20D expects the allowed value source to include at least:

- `UNSET`
- `APPROVE_SOURCE_RECOVERY_NEXT_AUDIT_ONLY`
- `REJECT_SOURCE_RECOVERY`
- `REQUEST_MORE_EVIDENCE`

All allowed values must remain no-action at this stage.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only`

Outputs:

- `GOLD_V2_20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_summary.json`
- `gold_v2_20d_input_audit.csv`
- `gold_v2_20d_content_checks.csv`
- `gold_v2_20d_required_field_audit.csv`
- `gold_v2_20d_allowed_value_audit.csv`
- `gold_v2_20d_required_next_gates.csv`
- `gold_v2_20d_stop_conditions.csv`
- `gold_v2_20d_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the unset actual decision intake draft content has passed audit-only content checks. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20D_DRAFT_CONTENT_AUDIT.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20d_draft_content_audit.py
pause
```

## Success conditions

20D succeeds only when all content checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY`

## Stop conditions

20D must stop when any required input is missing, upstream 20C did not pass, draft is no longer unset, actual decision collection is allowed, any decision/approval flag is true, any upstream STOP row exists, required field/value definitions are incomplete or duplicated, any restricted draft flag is true, any allowed value executes action, or any forbidden gate/summary flag is allowed.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20D_DRAFT_CONTENT_AUDIT_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20d_draft_content_audit.py`
- BAT: `scripts/gold_v2_runtime/bat/20D_DRAFT_CONTENT_AUDIT.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only/GOLD_V2_20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_summary.json`
- `FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only/gold_v2_20d_content_checks.csv`
- `FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only/gold_v2_20d_required_field_audit.csv`
- `FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only/gold_v2_20d_allowed_value_audit.csv`
- `FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only/gold_v2_20d_safety_matrix.csv`

## Do not run

Do not run actual decision collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

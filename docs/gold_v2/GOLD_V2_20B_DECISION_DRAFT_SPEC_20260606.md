# GOLD V2 20B actual decision intake draft audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20B prepares an audit-only draft package for a later actual human decision intake step after the 20A authorization gate passed.

20B is draft-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

The draft is intentionally still unset. It exists only to make the later intake fields, allowed values, required acknowledgements, and still-blocked actions inspectable before any actual decision value is entered.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

20B must not:

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

20B must stop unless 20A summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20B must also stop unless 20A authorization_gate_passed is true, total STOP rows are zero, authorization_scope is `ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY`, actual_decision_collection_allowed is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20A input folder:

`FX_OUTPUTS/gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only`

Required 20A inputs:

- `gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_summary.json`
- `gold_v2_20a_authorization_record.csv`
- `gold_v2_20a_authorization_checks.csv`
- `gold_v2_20a_required_next_gates.csv`
- `gold_v2_20a_safety_matrix.csv`
- `GOLD_V2_20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`

19H template-definition source inputs:

- `FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only/gold_v2_19h_actual_decision_template.json`
- `FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only/gold_v2_19h_required_decision_fields.csv`
- `FX_OUTPUTS/gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only/gold_v2_19h_allowed_decision_values.csv`

## Trade/strategy fields

20B does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Draft package

20B creates:

- `gold_v2_20b_decision_intake_draft.json`
- `gold_v2_20b_required_decision_fields.csv`
- `gold_v2_20b_allowed_decision_values.csv`

The draft must remain unset:

- `draft_status = DRAFT_ONLY_NOT_A_DECISION`
- `decision_value = UNSET`
- `decision_id = UNSET`
- `decision_timestamp_utc = UNSET`
- `human_reviewer = UNSET`
- `explicit_phrase = UNSET`
- `evidence_acknowledged = False`
- `approval_granted = False`
- all restricted action flags are False

## Audit method

20B audits:

- 20A status equals the expected success status
- 20A authorization_gate_passed is true
- 20A total_stop_rows is zero
- 20A actual_decision_collection_allowed is false
- 20A did not collect a decision, make a decision, or grant approval
- 20A checks and safety matrix have zero STOP rows
- 20A next gate allows 20B but keeps actual decision collection, source recovery, finalization, live, and final signal blocked
- 19H template, field, and value source files exist
- field/value definitions are copied without changing row counts
- draft remains unset and not a decision
- restricted draft flags remain false
- allowed decision values execute no action in the previous audit-only definition
- forbidden summary flags remain false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only`

Outputs:

- `GOLD_V2_20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json`
- `gold_v2_20b_input_audit.csv`
- `gold_v2_20b_decision_intake_draft.json`
- `gold_v2_20b_required_decision_fields.csv`
- `gold_v2_20b_allowed_decision_values.csv`
- `gold_v2_20b_draft_checks.csv`
- `gold_v2_20b_required_next_gates.csv`
- `gold_v2_20b_stop_conditions.csv`
- `gold_v2_20b_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that an unset actual decision intake draft package is ready for a later audit-only load-smoke/content audit. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20B_DECISION_DRAFT.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20b_decision_draft.py
pause
```

## Success conditions

20B succeeds only when all draft checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`

## Stop conditions

20B must stop when any required input is missing, upstream 20A did not pass, authorization scope is broader than preparation-only, any decision/approval flag is true, actual decision collection is allowed, any upstream STOP row exists, copied field/value definitions do not match, any restricted draft flag is true, or any forbidden gate/summary flag is allowed.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20B_DECISION_DRAFT_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20b_decision_draft.py`
- BAT: `scripts/gold_v2_runtime/bat/20B_DECISION_DRAFT.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/GOLD_V2_20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_decision_intake_draft.json`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_draft_checks.csv`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_safety_matrix.csv`

## Do not run

Do not run actual decision collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

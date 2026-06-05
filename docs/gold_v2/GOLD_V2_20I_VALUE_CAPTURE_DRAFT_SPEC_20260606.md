# GOLD V2 20I actual decision value capture draft audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20I prepares an audit-only draft package for a later actual decision value capture step after the 20H authorization gate passed.

20I is draft-only. It does not collect a decision value, does not infer a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any source recovery/live/final action block.

20I creates a structured value-capture draft whose decision value remains `UNSET`. A later, separately authorized step is required before any value can be captured.

## Backup requirement

Before adding 20I files, the following backup manifest must exist:

`docs/gold_v2/GOLD_V2_20I_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

20I must be new-file-only except that manifest. Existing signal/source/live files must not be modified.

## Hard prohibitions

20I must not:

- collect or infer an actual decision value
- approve source recovery or any other action
- promote the dry-run candidate identity ledger to source-of-truth
- execute source recovery
- finalize or recover source identity
- replay OHLC for source reconstruction
- enable live evaluator, live hook, or final signal behavior
- change signal conditions
- change candidate sets
- change TP/SL, entry, or exit logic
- send Discord or NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs
- make any MT5/Discord/live-side external action

## Upstream requirement

20I must stop unless 20H summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20I must also stop unless 20H authorization_gate_passed is true, total STOP rows are zero, decision_value is `UNSET`, actual_decision_collection_allowed is false, actual_decision_collection_completed is false, decision_value_collected is false, decision_collected is false, decision_made is false, approval_granted is false, signal_conditions_changed is false, and restricted execution flags remain false.

## Inputs

20H input folder:

`FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only`

Required 20H inputs:

- `gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_summary.json`
- `gold_v2_20h_authorization_record.csv`
- `gold_v2_20h_authorization_checks.csv`
- `gold_v2_20h_required_next_gates.csv`
- `gold_v2_20h_safety_matrix.csv`
- `GOLD_V2_20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`

Source draft inputs:

- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_allowed_decision_values.csv`
- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_required_decision_fields.csv`

Backup input:

- `docs/gold_v2/GOLD_V2_20I_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Trade/strategy fields

20I does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Draft outputs

20I writes:

- an unset value capture draft JSON
- a copy/audit of allowed decision values from the source-defined 20B table
- a copy/audit of required fields from the source-defined 20B table

The draft must keep:

- decision_value: `UNSET`
- actual_decision_value_collected: false
- actual_decision_collection_completed: false
- approval_granted: false
- source_recovery_allowed: false
- source_identity_finalization_allowed: false
- source_identity_recovery_allowed: false
- ledger_source_of_truth_promotion_allowed: false
- signal_conditions_change_allowed: false
- script_executes_action: false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only`

Outputs:

- `GOLD_V2_20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_summary.json`
- `gold_v2_20i_input_audit.csv`
- `gold_v2_20i_value_capture_draft.json`
- `gold_v2_20i_allowed_decision_values_audit.csv`
- `gold_v2_20i_required_decision_fields_audit.csv`
- `gold_v2_20i_draft_checks.csv`
- `gold_v2_20i_required_next_gates.csv`
- `gold_v2_20i_stop_conditions.csv`
- `gold_v2_20i_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the value capture draft is ready and still unset. It is not value capture, not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20I_VALUE_CAPTURE_DRAFT.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20i_value_capture_draft.py
pause
```

## Success conditions

20I succeeds only when all draft checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`

20I does not permit actual value capture, source recovery, finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

## Stop conditions

20I must stop when any required input is missing, backup manifest is missing, upstream 20H did not pass, any upstream STOP row exists, decision value is no longer UNSET, any decision/approval/value-collected flag is true, actual decision collection is completed/allowed, source-defined allowed values or required fields are missing/malformed/duplicated/action-executing, or any forbidden gate/summary flag is allowed.

## Implemented files

- Backup manifest: `docs/gold_v2/GOLD_V2_20I_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- Spec: `docs/gold_v2/GOLD_V2_20I_VALUE_CAPTURE_DRAFT_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20i_value_capture_draft.py`
- BAT: `scripts/gold_v2_runtime/bat/20I_VALUE_CAPTURE_DRAFT.bat`

## Do not run

Do not run actual decision value collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

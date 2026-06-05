# GOLD V2 20H actual decision value capture authorization gate audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20H records explicit human authorization to prepare the next audit-only actual decision value capture step.

20H is authorization-gate-only. It does not collect a decision value, does not infer a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any source recovery/live/final action block.

20H exists because 20G ended at:

`AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE`

The authorization scope of 20H is strictly:

`ACTUAL_DECISION_VALUE_CAPTURE_AUDIT_ONLY_PREPARATION_ONLY`

## Backup requirement

Before adding 20H files, the following backup manifest must exist:

`docs/gold_v2/GOLD_V2_20H_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

20H must be new-file-only except that manifest. Existing signal/source/live files must not be modified.

## Hard prohibitions

20H must not:

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

20H must stop unless 20G summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20H must also stop unless 20G handoff_ready is true, total STOP rows are zero, decision_value is `UNSET`, actual_decision_collection_allowed is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20G input folder:

`FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only`

Required 20G inputs:

- `gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_summary.json`
- `gold_v2_20g_handoff_checks.csv`
- `gold_v2_20g_final_handoff_note.md`
- `gold_v2_20g_required_next_gates.csv`
- `gold_v2_20g_safety_matrix.csv`
- `GOLD_V2_20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`

Backup input:

- `docs/gold_v2/GOLD_V2_20H_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Trade/strategy fields

20H does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Authorization record

20H writes an authorization record with:

- authorization_id: `GOLD_V2_20H_VALUE_CAPTURE_AUTH_20260606`
- authorization_text: `USER_AUTHORIZED_PROCEED_AFTER_20G_TO_ACTUAL_DECISION_VALUE_CAPTURE_AUDIT_ONLY_PREPARATION`
- authorization_scope: `ACTUAL_DECISION_VALUE_CAPTURE_AUDIT_ONLY_PREPARATION_ONLY`
- source: `current_chat_user_explicit_permission`
- allows_next_audit_only_value_capture_preparation: true

The record must explicitly keep false:

- actual_decision_value_collected
- actual_decision_collection_completed
- approval_granted
- source_recovery_allowed
- source_identity_finalization_allowed
- source_identity_recovery_allowed
- ledger_source_of_truth_promotion_allowed
- oh_lc_replay_allowed
- live_evaluator_allowed
- final_signal_allowed
- discord_send_allowed
- no_signal_discord_send_allowed
- mt5_order_allowed
- ai_api_allowed
- live_hook_allowed

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only`

Outputs:

- `GOLD_V2_20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_summary.json`
- `gold_v2_20h_input_audit.csv`
- `gold_v2_20h_authorization_record.csv`
- `gold_v2_20h_authorization_checks.csv`
- `gold_v2_20h_required_next_gates.csv`
- `gold_v2_20h_stop_conditions.csv`
- `gold_v2_20h_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that authorization was recorded to prepare a later audit-only decision value capture step. It is not value capture, not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20H_VALUE_CAPTURE_AUTH_GATE.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20h_value_capture_auth_gate.py
pause
```

## Success conditions

20H succeeds only when all authorization checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY`

20H does not permit source recovery, finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

## Stop conditions

20H must stop when any required input is missing, backup manifest is missing, upstream 20G did not pass, any upstream STOP row exists, decision value is no longer UNSET, any decision/approval flag is true, actual decision collection is completed, source recovery/finalization/live/final/Discord/MT5/AI flags are true, or any forbidden gate/summary flag is allowed.

## Implemented files

- Backup manifest: `docs/gold_v2/GOLD_V2_20H_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- Spec: `docs/gold_v2/GOLD_V2_20H_VALUE_CAPTURE_AUTH_GATE_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20h_value_capture_auth_gate.py`
- BAT: `scripts/gold_v2_runtime/bat/20H_VALUE_CAPTURE_AUTH_GATE.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only/GOLD_V2_20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_summary.json`
- `FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only/gold_v2_20h_authorization_record.csv`
- `FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only/gold_v2_20h_authorization_checks.csv`
- `FX_OUTPUTS/gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only/gold_v2_20h_safety_matrix.csv`

## Do not run

Do not run actual decision value collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

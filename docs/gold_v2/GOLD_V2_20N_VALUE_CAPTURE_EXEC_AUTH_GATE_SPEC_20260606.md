# GOLD V2 20N actual decision value capture execution authorization gate specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_AUTHORIZATION_GATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20N records explicit human authorization to prepare the next audit-only actual decision value capture execution step after the 20M final audit passed.

20N is authorization-gate-only. It does not collect a decision value, infer a decision value, approve anything, execute source recovery, finalize source identity, change signal rules, enable live/final paths, send Discord, place MT5 orders, or call AI APIs.

## Authorization source

The authorization text is the current chat instruction:

`20Mを確認しました。次は actual decision value capture execution の authorization gate を audit-only で準備してください。まだ source recovery / finalization / Discord / MT5 / AI API / live hook / live evaluator / final signal は許可しません。`

This authorizes only the preparation of the execution authorization gate. It does not provide a decision value and does not authorize source recovery or live actions.

## Required upstream status

20M summary status must be:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20M must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20M folder:

`FX_OUTPUTS/gold_v2_20m_tier2_source_identity_human_decision_value_capture_draft_final_audit_only`

Required files:

- `gold_v2_20m_tier2_source_identity_human_decision_value_capture_draft_final_audit_summary.json`
- `gold_v2_20m_final_checks.csv`
- `gold_v2_20m_stage_status_audit.csv`
- `gold_v2_20m_required_next_gates.csv`
- `gold_v2_20m_safety_matrix.csv`
- `GOLD_V2_20M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20N_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20n_tier2_source_identity_human_decision_value_capture_execution_authorization_gate_audit_only`

Outputs:

- `GOLD_V2_20N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20n_tier2_source_identity_human_decision_value_capture_execution_authorization_gate_summary.json`
- `gold_v2_20n_input_audit.csv`
- `gold_v2_20n_authorization_record.csv`
- `gold_v2_20n_authorization_checks.csv`
- `gold_v2_20n_required_next_gates.csv`
- `gold_v2_20n_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next gate

Only after success:

`20O_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_AUDIT_ONLY`

20N does not permit actual value collection, source recovery, source identity finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20n_value_capture_exec_auth_gate.py
pause
```

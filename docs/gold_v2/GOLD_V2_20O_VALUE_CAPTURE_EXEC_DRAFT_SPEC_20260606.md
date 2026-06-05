# GOLD V2 20O actual decision value capture execution draft specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20O_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20O prepares a still-UNSET audit-only execution draft after 20N authorization gate passed.

20O is execution-draft-only. It does not collect a decision value, infer a decision value, approve anything, execute source recovery, finalize source identity, change signal rules, enable live/final paths, send Discord, place MT5 orders, or call AI APIs.

## Required upstream status

20N summary status must be:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20N must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20N folder:

`FX_OUTPUTS/gold_v2_20n_tier2_source_identity_human_decision_value_capture_execution_authorization_gate_audit_only`

Required files:

- `gold_v2_20n_tier2_source_identity_human_decision_value_capture_execution_authorization_gate_summary.json`
- `gold_v2_20n_authorization_record.csv`
- `gold_v2_20n_authorization_checks.csv`
- `gold_v2_20n_required_next_gates.csv`
- `gold_v2_20n_safety_matrix.csv`
- `GOLD_V2_20N_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md`

20I draft source files:

- `FX_OUTPUTS/gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only/gold_v2_20i_value_capture_draft.json`
- `FX_OUTPUTS/gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only/gold_v2_20i_allowed_decision_values_audit.csv`
- `FX_OUTPUTS/gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only/gold_v2_20i_required_decision_fields_audit.csv`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20O_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_audit_only`

Outputs:

- `GOLD_V2_20O_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_summary.json`
- `gold_v2_20o_input_audit.csv`
- `gold_v2_20o_execution_draft.json`
- `gold_v2_20o_execution_draft_checks.csv`
- `gold_v2_20o_required_next_gates.csv`
- `gold_v2_20o_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next gate

Only after success:

`20P_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY`

20O does not permit actual value collection, source recovery, source identity finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20o_value_capture_exec_draft.py
pause
```

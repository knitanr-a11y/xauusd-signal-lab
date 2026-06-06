# GOLD V2 20S value capture execution draft final audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20S_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_ONLY`
Mode: audit-only

## Purpose

20S final-audits the reconciled still-UNSET execution draft chain after 20R passed.

20S does not collect a decision value and does not enable source or live action.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20R must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20R folder:

`FX_OUTPUTS/gold_v2_20r_tier2_source_identity_human_decision_value_capture_execution_draft_reconciliation_audit_only`

Required files:

- `gold_v2_20r_tier2_source_identity_human_decision_value_capture_execution_draft_reconciliation_summary.json`
- `gold_v2_20r_reconciliation_checks.csv`
- `gold_v2_20r_stage_status_audit.csv`
- `gold_v2_20r_required_next_gates.csv`
- `gold_v2_20r_safety_matrix.csv`
- `GOLD_V2_20R_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20S_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_only`

Outputs:

- `GOLD_V2_20S_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`
- `gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_summary.json`
- `gold_v2_20s_input_audit.csv`
- `gold_v2_20s_final_checks.csv`
- `gold_v2_20s_stage_status_audit.csv`
- `gold_v2_20s_required_next_gates.csv`
- `gold_v2_20s_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE_ACTUAL_VALUE_ENTRY`

20S still blocks source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20s_value_capture_exec_draft_final_audit.py
pause
```

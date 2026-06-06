# GOLD V2 20R actual decision value capture execution draft reconciliation specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20R_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

20R reconciles the still-UNSET 20Q execution draft content-audit package.

20R is reconciliation-only. It does not collect a decision value, infer a decision value, approve anything, execute source recovery, finalize source identity, change signal rules, enable live/final paths, send Discord, place MT5 orders, or call AI APIs.

## Required upstream status

20Q summary status must be:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20Q must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20Q folder:

`FX_OUTPUTS/gold_v2_20q_tier2_source_identity_human_decision_value_capture_execution_draft_content_audit_only`

Required files:

- `gold_v2_20q_tier2_source_identity_human_decision_value_capture_execution_draft_content_audit_summary.json`
- `gold_v2_20q_content_checks.csv`
- `gold_v2_20q_required_next_gates.csv`
- `gold_v2_20q_safety_matrix.csv`
- `GOLD_V2_20Q_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20R_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20r_tier2_source_identity_human_decision_value_capture_execution_draft_reconciliation_audit_only`

Outputs:

- `GOLD_V2_20R_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_20r_tier2_source_identity_human_decision_value_capture_execution_draft_reconciliation_summary.json`
- `gold_v2_20r_input_audit.csv`
- `gold_v2_20r_reconciliation_checks.csv`
- `gold_v2_20r_stage_status_audit.csv`
- `gold_v2_20r_required_next_gates.csv`
- `gold_v2_20r_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next gate

Only after success:

`20S_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_ONLY`

20R does not permit actual value collection, source recovery, source identity finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20r_value_capture_exec_draft_recon.py
pause
```

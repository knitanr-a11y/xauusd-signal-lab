# GOLD V2 20M value capture draft final audit specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_ONLY`
Mode: audit-only

## Purpose

20M final-audits the reconciled still-UNSET value capture draft chain.

20M is final-audit-only for the draft package. It does not collect a decision value, infer a decision value, approve anything, execute source recovery, finalize source identity, change signal rules, enable live/final paths, send Discord, place MT5 orders, or call AI APIs.

## Required upstream status

20L summary status must be:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20L must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20L folder:

`FX_OUTPUTS/gold_v2_20l_tier2_source_identity_human_decision_value_capture_draft_reconciliation_audit_only`

Required files:

- `gold_v2_20l_tier2_source_identity_human_decision_value_capture_draft_reconciliation_summary.json`
- `gold_v2_20l_reconciliation_checks.csv`
- `gold_v2_20l_stage_status_audit.csv`
- `gold_v2_20l_required_next_gates.csv`
- `gold_v2_20l_safety_matrix.csv`
- `GOLD_V2_20L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20M_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Final audit checks

20M checks:

- all inputs exist
- 20L status passed
- 20L STOP rows 0
- 20L reconciliation_passed true
- 20L and stage decision value remain `UNSET`
- reconciliation checks have STOP rows 0
- safety matrix has STOP rows 0
- forbidden next gates remain false
- restricted summary flags remain false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20m_tier2_source_identity_human_decision_value_capture_draft_final_audit_only`

Outputs:

- `GOLD_V2_20M_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`
- `gold_v2_20m_tier2_source_identity_human_decision_value_capture_draft_final_audit_summary.json`
- `gold_v2_20m_input_audit.csv`
- `gold_v2_20m_final_checks.csv`
- `gold_v2_20m_stage_status_audit.csv`
- `gold_v2_20m_required_next_gates.csv`
- `gold_v2_20m_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

Only after success:

`AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE_EXECUTION`

Actual decision collection, source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook remain blocked.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20m_value_capture_draft_final_audit.py
pause
```

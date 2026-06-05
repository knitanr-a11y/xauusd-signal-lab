# GOLD V2 20K value capture draft content audit specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20K content-audits the still-UNSET 20I value capture draft after 20J load-smoke passed.

20K is content-audit-only. It does not collect a decision value, infer a decision value, approve anything, execute source recovery, finalize source identity, change signal rules, enable live/final paths, send Discord, place MT5 orders, or call AI APIs.

## Required upstream status

20J summary status must be:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20J must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20J folder:

`FX_OUTPUTS/gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_audit_only`

Required files:

- `gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_summary.json`
- `gold_v2_20j_load_checks.csv`
- `gold_v2_20j_draft_load_audit.csv`
- `gold_v2_20j_required_next_gates.csv`
- `gold_v2_20j_safety_matrix.csv`
- `GOLD_V2_20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

20I folder:

`FX_OUTPUTS/gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only`

Required files:

- `gold_v2_20i_value_capture_draft.json`
- `gold_v2_20i_allowed_decision_values_audit.csv`
- `gold_v2_20i_required_decision_fields_audit.csv`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20K_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Audit checks

20K checks:

- all inputs exist
- 20J status passed
- 20J STOP rows 0
- 20J and draft decision value remains `UNSET`
- draft status is `VALUE_CAPTURE_DRAFT_ONLY_NOT_A_DECISION`
- allowed decision values have 4 or more rows, no empty values, no duplicates, no action-executing rows when an action column exists
- required fields have 6 or more rows, no duplicate field names
- draft required unset fields stay `UNSET`
- restricted flags stay false
- forbidden next gates remain false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_only`

Outputs:

- `GOLD_V2_20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20k_tier2_source_identity_human_decision_value_capture_draft_content_audit_summary.json`
- `gold_v2_20k_input_audit.csv`
- `gold_v2_20k_content_checks.csv`
- `gold_v2_20k_allowed_value_audit.csv`
- `gold_v2_20k_required_field_audit.csv`
- `gold_v2_20k_required_next_gates.csv`
- `gold_v2_20k_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next gate

Only after success:

`20L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_AUDIT_ONLY`

Actual decision collection, source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook remain blocked.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20k_value_capture_draft_content_audit.py
pause
```

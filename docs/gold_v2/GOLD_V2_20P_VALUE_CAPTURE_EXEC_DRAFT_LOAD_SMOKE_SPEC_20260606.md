# GOLD V2 20P actual decision value capture execution draft load-smoke specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20P_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20P load-smokes the still-UNSET 20O execution draft package.

20P is load-smoke-only. It does not collect a decision value, infer a decision value, approve anything, execute source recovery, finalize source identity, change signal rules, enable live/final paths, send Discord, place MT5 orders, or call AI APIs.

## Required upstream status

20O summary status must be:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20O must have STOP rows 0 and `decision_value=UNSET`.

## Inputs

20O folder:

`FX_OUTPUTS/gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_audit_only`

Required files:

- `gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_summary.json`
- `gold_v2_20o_execution_draft.json`
- `gold_v2_20o_execution_draft_checks.csv`
- `gold_v2_20o_required_next_gates.csv`
- `gold_v2_20o_safety_matrix.csv`
- `GOLD_V2_20O_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20P_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20p_tier2_source_identity_human_decision_value_capture_execution_draft_load_smoke_audit_only`

Outputs:

- `GOLD_V2_20P_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20p_tier2_source_identity_human_decision_value_capture_execution_draft_load_smoke_summary.json`
- `gold_v2_20p_input_audit.csv`
- `gold_v2_20p_draft_load_audit.csv`
- `gold_v2_20p_load_checks.csv`
- `gold_v2_20p_required_next_gates.csv`
- `gold_v2_20p_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next gate

Only after success:

`20Q_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_CONTENT_AUDIT_ONLY`

20P does not permit actual value collection, source recovery, source identity finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

## BAT

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20p_value_capture_exec_draft_load_smoke.py
pause
```

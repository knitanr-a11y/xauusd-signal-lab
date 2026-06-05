# GOLD V2 20J actual decision value capture draft load-smoke audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20J load-smokes the 20I value capture draft package.

20J is load-smoke-only. It does not collect a decision value, infer a decision value, approve anything, make a human decision, promote source-of-truth, execute source recovery, or relax any live/final/Discord/MT5/AI block.

20J confirms the 20I draft JSON and associated audit outputs can be loaded and remain `UNSET`/no-action.

## Backup requirement

Before adding 20J files, the following backup manifest must exist:

`docs/gold_v2/GOLD_V2_20J_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Hard prohibitions

20J must not:

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

20J must stop unless 20I summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20J must also stop unless 20I draft_ready is true, total STOP rows are zero, decision_value is `UNSET`, actual decision value has not been collected, actual decision collection is not completed/allowed, approval is false, signal_conditions_changed is false, and restricted execution flags remain false.

## Inputs

20I input folder:

`FX_OUTPUTS/gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_audit_only`

Required inputs:

- `gold_v2_20i_tier2_source_identity_human_decision_value_capture_draft_summary.json`
- `gold_v2_20i_value_capture_draft.json`
- `gold_v2_20i_draft_checks.csv`
- `gold_v2_20i_allowed_decision_values_audit.csv`
- `gold_v2_20i_required_decision_fields_audit.csv`
- `gold_v2_20i_required_next_gates.csv`
- `gold_v2_20i_safety_matrix.csv`
- `GOLD_V2_20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY_REPORT.md`

Backup input:

- `docs/gold_v2/GOLD_V2_20J_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Trade/strategy fields

20J does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_audit_only`

Outputs:

- `GOLD_V2_20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20j_tier2_source_identity_human_decision_value_capture_draft_load_smoke_summary.json`
- `gold_v2_20j_input_audit.csv`
- `gold_v2_20j_draft_load_audit.csv`
- `gold_v2_20j_load_checks.csv`
- `gold_v2_20j_required_next_gates.csv`
- `gold_v2_20j_stop_conditions.csv`
- `gold_v2_20j_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the still-UNSET 20I draft loaded successfully. It is not value capture, not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from repository root:

```bat
scripts\gold_v2_runtime\bat\20J_VALUE_CAPTURE_DRAFT_LOAD_SMOKE.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20j_value_capture_draft_load_smoke.py
pause
```

## Success conditions

20J succeeds only when all load checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_ONLY`

20J does not permit actual value capture, source recovery, finalization, live evaluator, final signal, Discord, MT5, AI API, or live hook.

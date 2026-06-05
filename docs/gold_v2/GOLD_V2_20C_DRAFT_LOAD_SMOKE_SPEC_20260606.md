# GOLD V2 20C actual decision intake draft load-smoke audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20C load-smokes the unset actual decision intake draft package produced by 20B.

20C is load-smoke-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

20C must not:

- collect or infer an actual decision value
- approve source recovery or any other action
- promote the dry-run candidate identity ledger to source-of-truth
- execute source recovery
- finalize or recover source identity
- replay OHLC for source reconstruction
- enable live evaluator, live hook, or final signal behavior
- send Discord or NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs
- make any MT5/Discord/live-side external action

## Upstream requirement

20C must stop unless 20B summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20C must also stop unless 20B draft_ready is true, total STOP rows are zero, draft_status is `DRAFT_ONLY_NOT_A_DECISION`, decision_value is `UNSET`, actual_decision_collection_allowed is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20B input folder:

`FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only`

Required 20B inputs:

- `gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json`
- `gold_v2_20b_decision_intake_draft.json`
- `gold_v2_20b_required_decision_fields.csv`
- `gold_v2_20b_allowed_decision_values.csv`
- `gold_v2_20b_draft_checks.csv`
- `gold_v2_20b_required_next_gates.csv`
- `gold_v2_20b_safety_matrix.csv`
- `GOLD_V2_20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY_REPORT.md`

## Trade/strategy fields

20C does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Load-smoke checks

20C loads the 20B draft JSON and copied field/value CSVs, then checks:

- draft JSON loads
- draft_status is `DRAFT_ONLY_NOT_A_DECISION`
- decision value and required human-input fields are still `UNSET`
- evidence_acknowledged is false
- actual_decision_collection_allowed is false
- approval_granted is false
- restricted draft flags are false
- required field rows are present
- allowed value rows are present
- allowed decision values execute no action
- 20B checks/safety have zero STOP rows
- forbidden next gates remain blocked

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only`

Outputs:

- `GOLD_V2_20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json`
- `gold_v2_20c_input_audit.csv`
- `gold_v2_20c_draft_load_audit.csv`
- `gold_v2_20c_load_checks.csv`
- `gold_v2_20c_required_next_gates.csv`
- `gold_v2_20c_stop_conditions.csv`
- `gold_v2_20c_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the unset actual decision intake draft can be loaded and still has no decision/approval/action. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20C_DRAFT_LOAD_SMOKE.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20c_draft_load_smoke.py
pause
```

## Success conditions

20C succeeds only when all load-smoke checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY`

## Stop conditions

20C must stop when any required input is missing, upstream 20B did not pass, draft loading fails, draft is no longer unset, actual decision collection is allowed, any decision/approval flag is true, any upstream STOP row exists, any restricted draft flag is true, any allowed value executes action, or any forbidden gate/summary flag is allowed.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20C_DRAFT_LOAD_SMOKE_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20c_draft_load_smoke.py`
- BAT: `scripts/gold_v2_runtime/bat/20C_DRAFT_LOAD_SMOKE.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only/GOLD_V2_20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json`
- `FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only/gold_v2_20c_draft_load_audit.csv`
- `FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only/gold_v2_20c_load_checks.csv`
- `FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only/gold_v2_20c_safety_matrix.csv`

## Do not run

Do not run actual decision collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

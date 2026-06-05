# GOLD V2 20E actual decision intake draft reconciliation audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

20E reconciles the 20B draft preparation, 20C draft load-smoke, and 20D draft content audit outputs.

20E is reconciliation-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

20E exists to confirm that the draft package is consistently unset across 20B/20C/20D and that the next step may remain an audit-only final review of the draft package, not actual decision collection.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

20E must not:

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

## Upstream requirements

20E must stop unless the upstream statuses are:

- 20B: `TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`
- 20C: `TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`
- 20D: `TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20E must also stop unless all upstream STOP rows are zero, all decision values are `UNSET`, actual decision collection is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20B input folder:

`FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only`

Required 20B inputs:

- `gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json`
- `gold_v2_20b_decision_intake_draft.json`
- `gold_v2_20b_draft_checks.csv`
- `gold_v2_20b_required_next_gates.csv`
- `gold_v2_20b_safety_matrix.csv`

20C input folder:

`FX_OUTPUTS/gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only`

Required 20C inputs:

- `gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json`
- `gold_v2_20c_draft_load_audit.csv`
- `gold_v2_20c_load_checks.csv`
- `gold_v2_20c_required_next_gates.csv`
- `gold_v2_20c_safety_matrix.csv`

20D input folder:

`FX_OUTPUTS/gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only`

Required 20D inputs:

- `gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_summary.json`
- `gold_v2_20d_content_checks.csv`
- `gold_v2_20d_required_field_audit.csv`
- `gold_v2_20d_allowed_value_audit.csv`
- `gold_v2_20d_required_next_gates.csv`
- `gold_v2_20d_safety_matrix.csv`
- `GOLD_V2_20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md`

## Trade/strategy fields

20E does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Reconciliation checks

20E checks:

- 20B, 20C, and 20D statuses are the expected pass statuses
- 20B draft_ready, 20C draft_load_smoke_passed, and 20D content_audit_passed are true
- all upstream summaries report total_stop_rows = 0
- all upstream check/audit/safety CSVs contain zero STOP rows
- 20B/20C/20D decision values are all `UNSET`
- 20B/20C/20D decision_collected, decision_made, approval_granted, and actual_decision_collection_allowed are all false
- 20B/20C/20D field/value row counts match where available
- forbidden gates remain blocked
- forbidden summary flags remain false
- draft JSON remains unset and no-action

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only`

Outputs:

- `GOLD_V2_20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_summary.json`
- `gold_v2_20e_input_audit.csv`
- `gold_v2_20e_reconciliation_checks.csv`
- `gold_v2_20e_stage_status_audit.csv`
- `gold_v2_20e_required_next_gates.csv`
- `gold_v2_20e_stop_conditions.csv`
- `gold_v2_20e_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the unset actual decision intake draft package has reconciled across 20B/20C/20D. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20E_DRAFT_RECON.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20e_draft_recon.py
pause
```

## Success conditions

20E succeeds only when all reconciliation checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY`

## Stop conditions

20E must stop when any required input is missing, any upstream status did not pass, any upstream STOP row exists, any stage reports a decision/approval/collection, actual decision collection is allowed, field/value row counts conflict, any forbidden gate/summary flag is allowed, or the draft is no longer unset/no-action.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20E_DRAFT_RECON_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20e_draft_recon.py`
- BAT: `scripts/gold_v2_runtime/bat/20E_DRAFT_RECON.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only/GOLD_V2_20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_summary.json`
- `FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only/gold_v2_20e_reconciliation_checks.csv`
- `FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only/gold_v2_20e_stage_status_audit.csv`
- `FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only/gold_v2_20e_safety_matrix.csv`

## Do not run

Do not run actual decision collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

# GOLD V2 20F actual decision intake draft final audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY`
Mode: audit-only

## Purpose

20F performs the final audit-only review of the unset actual decision intake draft package after the 20E reconciliation passed.

20F is final-audit-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

20F exists to confirm that the draft package remains consistently unset and no-action after the preparation, load-smoke, content audit, and reconciliation sequence. It prepares only a later final handoff audit-only step.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

20F must not:

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

20F must stop unless 20E summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20F must also stop unless 20E reconciliation_passed is true, total STOP rows are zero, decision_value is `UNSET`, actual_decision_collection_allowed is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20E input folder:

`FX_OUTPUTS/gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only`

Required 20E inputs:

- `gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_summary.json`
- `gold_v2_20e_reconciliation_checks.csv`
- `gold_v2_20e_stage_status_audit.csv`
- `gold_v2_20e_required_next_gates.csv`
- `gold_v2_20e_safety_matrix.csv`
- `GOLD_V2_20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md`

20B draft source input:

- `FX_OUTPUTS/gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only/gold_v2_20b_decision_intake_draft.json`

## Trade/strategy fields

20F does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Final audit checks

20F checks:

- 20E status equals the expected pass status
- 20E reconciliation_passed is true
- 20E summary total_stop_rows is zero
- 20E reconciliation checks and safety matrix contain zero STOP rows
- 20E stage status audit confirms 20B/20C/20D statuses passed
- 20E stage status audit confirms all decision values are `UNSET`
- 20E stage status audit confirms all upstream summary STOP rows are zero
- 20E next gate allows only 20F while forbidden gates remain blocked
- 20B draft JSON remains unset and no-action
- forbidden summary flags remain false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only`

Outputs:

- `GOLD_V2_20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`
- `gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_summary.json`
- `gold_v2_20f_input_audit.csv`
- `gold_v2_20f_final_checks.csv`
- `gold_v2_20f_required_next_gates.csv`
- `gold_v2_20f_stop_conditions.csv`
- `gold_v2_20f_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the unset actual decision intake draft package has passed final audit-only review. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20F_DRAFT_FINAL_AUDIT.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20f_draft_final_audit.py
pause
```

## Success conditions

20F succeeds only when all final checks are PASS and `total_stop_rows` is 0.

The only next recommended gate after success is:

`20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY`

20F does not permit actual decision collection. A later explicit human authorization gate is still required before any actual decision value can be collected.

## Stop conditions

20F must stop when any required input is missing, upstream 20E did not pass, any upstream STOP row exists, any stage status is not passed, any decision value is no longer UNSET, any decision/approval flag is true, actual decision collection is allowed, any restricted draft flag is true, or any forbidden gate/summary flag is allowed.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20F_DRAFT_FINAL_AUDIT_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20f_draft_final_audit.py`
- BAT: `scripts/gold_v2_runtime/bat/20F_DRAFT_FINAL_AUDIT.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only/GOLD_V2_20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_summary.json`
- `FX_OUTPUTS/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only/gold_v2_20f_final_checks.csv`
- `FX_OUTPUTS/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only/gold_v2_20f_safety_matrix.csv`

## Do not run

Do not run actual decision collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

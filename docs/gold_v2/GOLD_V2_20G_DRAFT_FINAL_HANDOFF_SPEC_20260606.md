# GOLD V2 20G actual decision intake draft final handoff audit-only specification

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY`
Mode: audit-only

## Purpose

20G prepares the final audit-only handoff note for the unset actual decision intake draft package after 20F final audit passed.

20G is handoff-note-only. It does not collect a decision value, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

20G marks the draft preparation chain as ready for a later explicit human authorization gate before any actual decision value can be captured. It does not itself authorize actual decision collection.

## Hard prohibitions

20G must not:

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

20G must stop unless 20F summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20G must also stop unless 20F final_audit_ready is true, total STOP rows are zero, decision_value is `UNSET`, actual_decision_collection_allowed is false, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

20F input folder:

`FX_OUTPUTS/gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_only`

Required 20F inputs:

- `gold_v2_20f_tier2_source_identity_human_decision_intake_draft_final_audit_summary.json`
- `gold_v2_20f_final_checks.csv`
- `gold_v2_20f_required_next_gates.csv`
- `gold_v2_20f_safety_matrix.csv`
- `GOLD_V2_20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY_REPORT.md`

## Trade/strategy fields

20G does not evaluate trades and does not read OHLC or trade ledgers.

- input CSV for trades: not applicable
- output CSV for trades: not applicable
- strategy_id: not applicable
- entry_time: not applicable
- direction: not applicable
- TP/SL: not applicable
- outcome: not applicable
- expected trade count: 0
- AI API: not called

## Handoff note

20G writes a handoff note stating:

- the draft package is still unset
- no actual decision value has been collected
- no approval has been granted
- actual decision collection is still blocked
- source recovery, source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord are still blocked
- a later explicit human authorization gate is required before any actual decision value capture step

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only`

Outputs:

- `GOLD_V2_20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`
- `gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_summary.json`
- `gold_v2_20g_input_audit.csv`
- `gold_v2_20g_handoff_checks.csv`
- `gold_v2_20g_final_handoff_note.md`
- `gold_v2_20g_required_next_gates.csv`
- `gold_v2_20g_stop_conditions.csv`
- `gold_v2_20g_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the unset actual decision intake draft package has a final audit-only handoff note. It is not a human decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## BAT execution

Run from the repository root with:

```bat
scripts\gold_v2_runtime\bat\20G_DRAFT_FINAL_HANDOFF.bat
```

The BAT must contain only:

```bat
@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_20g_draft_final_handoff.py
pause
```

## Success conditions

20G succeeds only when all handoff checks are PASS and `total_stop_rows` is 0.

The only next recommended state after success is:

`AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE`

20G does not permit actual decision collection. A later explicit human authorization gate is required before any actual decision value can be collected.

## Stop conditions

20G must stop when any required input is missing, upstream 20F did not pass, any upstream STOP row exists, decision value is no longer UNSET, any decision/approval flag is true, actual decision collection is allowed, any forbidden gate/summary flag is allowed, or the handoff note does not preserve all prohibitions.

## Implemented files

- Spec: `docs/gold_v2/GOLD_V2_20G_DRAFT_FINAL_HANDOFF_SPEC_20260606.md`
- Script: `scripts/gold_v2_runtime/audit_gold_v2_20g_draft_final_handoff.py`
- BAT: `scripts/gold_v2_runtime/bat/20G_DRAFT_FINAL_HANDOFF.bat`

## Files to inspect after running

- `FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only/GOLD_V2_20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_summary.json`
- `FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only/gold_v2_20g_final_handoff_note.md`
- `FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only/gold_v2_20g_handoff_checks.csv`
- `FX_OUTPUTS/gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only/gold_v2_20g_safety_matrix.csv`

## Do not run

Do not run actual decision collection, source recovery, source identity finalization, live evaluator, live hook, final signal, Discord send, MT5 order, AI API, or NO_SIGNAL Discord notification from this step.

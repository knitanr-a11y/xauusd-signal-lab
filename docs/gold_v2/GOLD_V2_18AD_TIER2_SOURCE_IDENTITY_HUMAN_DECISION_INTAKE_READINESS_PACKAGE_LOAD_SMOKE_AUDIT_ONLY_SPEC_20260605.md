# GOLD V2 18AD TIER2 source identity human decision intake readiness package load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AD load-smokes the 18AC human-decision intake readiness package.

18AD is load-smoke only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18AD must not:

- promote the dry-run candidate identity ledger to source-of-truth
- execute source recovery
- finalize or recover source identity
- replay OHLC for source reconstruction
- enable live or final evaluator behavior
- send Discord or NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs
- call live hooks

## Upstream requirement

18AD must stop unless 18AC summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AD must also stop unless 18AC readiness_package_prepared is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18AC output folder:

`FX_OUTPUTS/gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only`

Required 18AC inputs:

- `gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_summary.json`
- `gold_v2_18ac_package_checks.csv`
- `gold_v2_18ac_evidence_package_index.csv`
- `gold_v2_18ac_blocker_package_summary.csv`
- `gold_v2_18ac_required_next_gates.csv`
- `gold_v2_18ac_safety_matrix.csv`
- `GOLD_V2_18AC_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md`

Reference summaries from 18K through 18AC may be read for safety context only.

## Load-smoke checks

18AD checks:

- 18AC status is expected success
- 18AC readiness_package_prepared is true
- 18AC total STOP rows is zero
- 18AC decision_collected, decision_made, and approval_granted are false
- 18AC package checks and safety matrix have zero STOP rows
- 18AC evidence package index loads and all indexed evidence exists
- package_use remains evidence-only
- blocker package summary loads and still reports blockers in force
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only`

Outputs:

- `GOLD_V2_18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_summary.json`
- `gold_v2_18ad_input_audit.csv`
- `gold_v2_18ad_load_checks.csv`
- `gold_v2_18ad_package_index_load_audit.csv`
- `gold_v2_18ad_blocker_summary_load_audit.csv`
- `gold_v2_18ad_required_next_gates.csv`
- `gold_v2_18ad_stop_conditions.csv`
- `gold_v2_18ad_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that the 18AC readiness package loaded safely. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY`

18AE may content-audit the 18AC readiness package. 18AE must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

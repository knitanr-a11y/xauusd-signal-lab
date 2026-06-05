# GOLD V2 18AD load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AD load-smokes the 18AC human-decision intake readiness package.

This short-path spec replaces the previous long-path 18AD spec so GitHub Desktop can checkout the repository on Windows. The audit scope is unchanged.

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

## Required next gate

`18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY`

18AE may content-audit the 18AC readiness package. It must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

# GOLD V2 18AF readiness package reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AF reconciles the 18AC readiness package, the 18AD load-smoke result, and the 18AE content-audit result.

18AF is reconciliation-only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

18AF must not:

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

18AF must stop unless 18AE summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AF must also stop unless 18AE package_content_audit_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

Required folders:

- `FX_OUTPUTS/gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only`
- `FX_OUTPUTS/gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only`
- `FX_OUTPUTS/gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_only`

Required 18AE inputs:

- `gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_summary.json`
- `gold_v2_18ae_content_checks.csv`
- `gold_v2_18ae_package_index_content_audit.csv`
- `gold_v2_18ae_blocker_summary_content_audit.csv`
- `gold_v2_18ae_required_next_gates.csv`
- `gold_v2_18ae_safety_matrix.csv`
- `GOLD_V2_18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY_REPORT.md`

Required 18AD and 18AC evidence is used only for reconciliation.

## Reconciliation checks

18AF checks:

- 18AE status is expected success
- 18AE package_content_audit_passed is true
- 18AE total STOP rows is zero
- 18AC, 18AD, and 18AE all keep decision_collected false, decision_made false, and approval_granted false
- 18AD and 18AE check/safety tables have zero STOP rows
- 18AC package index row count reconciles with 18AD load audit and 18AE content audit
- 18AC blocker package summary reconciles with 18AD and 18AE blocker checks
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_audit_only`

Outputs:

- `GOLD_V2_18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_summary.json`
- `gold_v2_18af_input_audit.csv`
- `gold_v2_18af_reconciliation_checks.csv`
- `gold_v2_18af_package_index_reconciliation.csv`
- `gold_v2_18af_blocker_summary_reconciliation.csv`
- `gold_v2_18af_required_next_gates.csv`
- `gold_v2_18af_stop_conditions.csv`
- `gold_v2_18af_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Required next gate

`18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY`

18AG may review blockers after package reconciliation. It must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

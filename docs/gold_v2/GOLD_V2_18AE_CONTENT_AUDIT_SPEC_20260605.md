# GOLD V2 18AE readiness package content audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

18AE content-audits the 18AC readiness package after 18AD load-smoke passed.

18AE is content-audit only. It does not collect a decision, does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

This spec intentionally uses a short repository path to avoid Windows/GitHub Desktop checkout failures.

## Hard prohibitions

18AE must not:

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

18AE must stop unless 18AD summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18AE must also stop unless 18AD package_load_smoke_passed is true, total STOP rows are zero, decision_collected is false, decision_made is false, approval_granted is false, and restricted execution flags remain false.

## Inputs

18AD output folder:

`FX_OUTPUTS/gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only`

Required 18AD inputs:

- `gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_summary.json`
- `gold_v2_18ad_load_checks.csv`
- `gold_v2_18ad_package_index_load_audit.csv`
- `gold_v2_18ad_blocker_summary_load_audit.csv`
- `gold_v2_18ad_required_next_gates.csv`
- `gold_v2_18ad_safety_matrix.csv`
- `GOLD_V2_18AD_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

18AC output folder:

`FX_OUTPUTS/gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only`

Required 18AC inputs:

- `gold_v2_18ac_evidence_package_index.csv`
- `gold_v2_18ac_blocker_package_summary.csv`

## Content checks

18AE checks:

- 18AD status is expected success
- 18AD load checks, package index load audit, and safety matrix have zero STOP rows
- package index roles are unique and every row is evidence-only
- package index contains required evidence roles from 18X through 18AB
- blocker package summary contains blocker_rows, must_remain_blocked_false_rows, script_can_clear_true_rows, and template_decision_value
- blockers remain present, blocked, not script-clearable, and template remains UNSET
- source recovery, source identity finalization, live, and final signal remain blocked by next gates
- reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_only`

Outputs:

- `GOLD_V2_18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_summary.json`
- `gold_v2_18ae_input_audit.csv`
- `gold_v2_18ae_content_checks.csv`
- `gold_v2_18ae_package_index_content_audit.csv`
- `gold_v2_18ae_blocker_summary_content_audit.csv`
- `gold_v2_18ae_required_next_gates.csv`
- `gold_v2_18ae_stop_conditions.csv`
- `gold_v2_18ae_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Required next gate

`18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY`

18AF may reconcile 18AC/18AD/18AE readiness package evidence only. It must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

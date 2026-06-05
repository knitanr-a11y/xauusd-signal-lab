# GOLD V2 18U TIER2 source identity human review packet reconciliation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

18U reconciles the human-review packet evidence produced by 18R, validated by 18S, and content-audited by 18T.

18U is a reconciliation-only step. It does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18U must not:

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

18U must stop unless 18T summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18U must also stop unless 18T content audit passed, total STOP rows are zero, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18R output folder:

`FX_OUTPUTS/gold_v2_18r_tier2_source_identity_human_review_packet_audit_only`

18S output folder:

`FX_OUTPUTS/gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only`

18T output folder:

`FX_OUTPUTS/gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only`

Required 18T inputs:

- `gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_summary.json`
- `gold_v2_18t_content_checks.csv`
- `gold_v2_18t_packet_section_audit.csv`
- `gold_v2_18t_manual_question_content_audit.csv`
- `gold_v2_18t_blocked_action_content_audit.csv`
- `gold_v2_18t_required_next_gates.csv`
- `gold_v2_18t_safety_matrix.csv`
- `GOLD_V2_18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY_REPORT.md`

Required 18S inputs:

- `gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json`
- `gold_v2_18s_load_checks.csv`
- `gold_v2_18s_required_next_gates.csv`
- `gold_v2_18s_safety_matrix.csv`

Required 18R inputs:

- `gold_v2_18r_tier2_source_identity_human_review_packet_summary.json`
- `gold_v2_18r_human_review_packet_index.csv`
- `gold_v2_18r_manual_decision_questions.csv`
- `gold_v2_18r_actions_still_blocked.csv`
- `gold_v2_18r_required_next_gates.csv`
- `gold_v2_18r_safety_matrix.csv`

Reference summaries from 18K through 18Q may be read for safety context only.

## Reconciliation checks

18U checks:

- 18T status is expected success
- 18T content_audit_passed is true
- 18T total STOP rows is zero
- 18R, 18S, and 18T all report decision_made false and approval_granted false
- 18R packet index item count reconciles with 18S packet files checked
- 18R blocked action count reconciles with 18T blocked action audit
- 18R manual question count reconciles with 18S and 18T manual-question audits
- 18S and 18T check tables contain zero STOP rows
- 18R, 18S, and 18T next gates keep source recovery, source identity finalization, live, and final signal blocked
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only`

Outputs:

- `GOLD_V2_18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_summary.json`
- `gold_v2_18u_input_audit.csv`
- `gold_v2_18u_reconciliation_checks.csv`
- `gold_v2_18u_packet_count_reconciliation.csv`
- `gold_v2_18u_blocked_action_reconciliation.csv`
- `gold_v2_18u_manual_question_reconciliation.csv`
- `gold_v2_18u_required_next_gates.csv`
- `gold_v2_18u_stop_conditions.csv`
- `gold_v2_18u_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that 18R/18S/18T packet evidence reconciled. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18V_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY`

18V may summarize remaining blockers for human review. It must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

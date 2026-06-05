# GOLD V2 18W TIER2 source identity human review decision packet audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY`
Mode: audit-only

## Purpose

18W prepares a final human-review decision packet after 18V blocker summary passed.

18W is packet-preparation only. It does not approve anything, does not make a human decision, does not promote any ledger to source-of-truth, and does not relax any blocked action.

## Hard prohibitions

18W must not:

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

18W must stop unless 18V summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18W must also stop unless 18V blocker_summary_prepared is true, total STOP rows are zero, decision_made is false, approval_granted is false, and all restricted execution flags remain false.

## Inputs

18V output folder:

`FX_OUTPUTS/gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only`

Required 18V inputs:

- `gold_v2_18v_tier2_source_identity_human_review_blocker_summary.json`
- `gold_v2_18v_blocker_summary_checks.csv`
- `gold_v2_18v_remaining_blockers.csv`
- `gold_v2_18v_manual_decision_summary.csv`
- `gold_v2_18v_required_next_gates.csv`
- `gold_v2_18v_safety_matrix.csv`
- `GOLD_V2_18V_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_BLOCKER_SUMMARY_AUDIT_ONLY_REPORT.md`

18R output folder:

`FX_OUTPUTS/gold_v2_18r_tier2_source_identity_human_review_packet_audit_only`

Required 18R inputs:

- `gold_v2_18r_human_review_packet_markdown.md`
- `gold_v2_18r_manual_decision_questions.csv`
- `gold_v2_18r_actions_still_blocked.csv`

Reference summaries from 18K through 18V may be read for safety context only.

## Packet checks

18W checks:

- 18V status is expected success
- 18V blocker_summary_prepared is true
- 18V total STOP rows is zero
- 18V decision_made and approval_granted are false
- 18V safety matrix has zero STOP rows
- remaining blockers count is non-zero and every row remains blocking
- manual questions are present and remain no-script-decision
- decision options are listed as human-only choices
- no source recovery/finalization/live/final path is allowed by next gates
- all reference summaries keep restricted execution flags false

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only`

Outputs:

- `GOLD_V2_18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY_REPORT.md`
- `gold_v2_18w_tier2_source_identity_human_review_decision_packet_summary.json`
- `gold_v2_18w_input_audit.csv`
- `gold_v2_18w_decision_packet_checks.csv`
- `gold_v2_18w_human_decision_options.csv`
- `gold_v2_18w_decision_packet_markdown.md`
- `gold_v2_18w_required_next_gates.csv`
- `gold_v2_18w_stop_conditions.csv`
- `gold_v2_18w_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that a decision packet was prepared for human review. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY`

18X may plan how to intake an explicit human decision later. 18X must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

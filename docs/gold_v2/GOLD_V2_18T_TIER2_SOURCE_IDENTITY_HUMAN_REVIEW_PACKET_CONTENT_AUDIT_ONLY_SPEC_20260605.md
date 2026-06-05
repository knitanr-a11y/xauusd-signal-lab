# GOLD V2 18T TIER2 source identity human review packet content audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY`
Mode: audit-only

## Purpose

18T performs a content audit of the 18R human-review packet after 18S load-smoke passed.

18T checks that the packet contains the required manual-review sections, required blocked-action evidence, and required safety state. It does not approve anything, does not make a human decision, and does not relax any blocker.

## Hard prohibitions

18T must not:

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

18T must stop unless 18S summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18T must also stop unless 18S passed, total STOP rows are zero, decision_made is false, approval_granted is false, and all forbidden execution flags remain false.

## Inputs

18S output folder:

`FX_OUTPUTS/gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only`

Required 18S inputs:

- `gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json`
- `gold_v2_18s_load_checks.csv`
- `gold_v2_18s_packet_file_audit.csv`
- `gold_v2_18s_markdown_audit.csv`
- `gold_v2_18s_manual_question_audit.csv`
- `gold_v2_18s_blocked_action_audit.csv`
- `gold_v2_18s_required_next_gates.csv`
- `gold_v2_18s_safety_matrix.csv`
- `GOLD_V2_18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

18R output folder:

`FX_OUTPUTS/gold_v2_18r_tier2_source_identity_human_review_packet_audit_only`

Required 18R packet inputs:

- `gold_v2_18r_human_review_packet_markdown.md`
- `gold_v2_18r_manual_decision_questions.csv`
- `gold_v2_18r_actions_still_blocked.csv`
- `gold_v2_18r_required_next_gates.csv`
- `gold_v2_18r_safety_matrix.csv`

Reference summaries from 18K through 18R may be read for safety context only.

## Content checks

18T checks:

- 18S status is the expected 18S success status
- 18S packet_load_smoke_passed is true
- 18S total STOP rows is zero
- 18S decision_made and approval_granted are false
- 18S load checks, packet file audit, markdown audit, manual question audit, blocked action audit, and safety matrix all have zero STOP rows
- 18R markdown loads and contains the major human-review sections
- 18R manual decision questions are all manual-only and no-script-decision
- 18R blocked actions include the required blocked categories and remain BLOCKED
- 18R/18S next gates allow only the next audit-only step and keep source recovery, source identity finalization, live, and final signal blocked
- all reference summaries keep forbidden flags false

18T does not require exact wording such as every individual `not ...` phrase. It only checks section presence, blocked-action coverage, and absence of affirmative approval/execution language.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only`

Outputs:

- `GOLD_V2_18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY_REPORT.md`
- `gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_summary.json`
- `gold_v2_18t_input_audit.csv`
- `gold_v2_18t_content_checks.csv`
- `gold_v2_18t_packet_section_audit.csv`
- `gold_v2_18t_manual_question_content_audit.csv`
- `gold_v2_18t_blocked_action_content_audit.csv`
- `gold_v2_18t_required_next_gates.csv`
- `gold_v2_18t_stop_conditions.csv`
- `gold_v2_18t_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This means only that packet content audit passed. It is not a decision, not approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18U_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_RECONCILIATION_AUDIT_ONLY`

18U may reconcile 18R/18S/18T packet evidence. 18U must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

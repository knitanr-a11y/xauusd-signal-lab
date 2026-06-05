# GOLD V2 18S TIER2 source identity human review packet load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

18S validates that the 18R human-review packet outputs load correctly and still preserve all audit-only safety constraints.

18S is not an approval step and must not make a decision. It only load-smoke checks packet files, packet index, manual decision questions, blocked actions, next gates, and safety matrix.

18S must not promote the dry-run candidate identity ledger to source-of-truth. It must not execute source recovery, finalize source identity, recover source identity, implement live/final evaluator behavior, replay OHLC, send Discord notifications, send NO_SIGNAL Discord notifications, place MT5 orders, call AI APIs, or call live hooks.

## Upstream requirements

18S must stop unless 18R summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18S must also stop unless 18R human-review packet is ready, no decision or approval was made, all 18R STOP rows are zero, and all forbidden safety flags remain false.

## Inputs

18R outputs from:

`FX_OUTPUTS/gold_v2_18r_tier2_source_identity_human_review_packet_audit_only`

- `gold_v2_18r_tier2_source_identity_human_review_packet_summary.json`
- `gold_v2_18r_input_audit.csv`
- `gold_v2_18r_packet_checks.csv`
- `gold_v2_18r_human_review_packet_index.csv`
- `gold_v2_18r_human_review_packet_markdown.md`
- `gold_v2_18r_manual_decision_questions.csv`
- `gold_v2_18r_actions_still_blocked.csv`
- `gold_v2_18r_required_next_gates.csv`
- `gold_v2_18r_stop_conditions.csv`
- `gold_v2_18r_safety_matrix.csv`
- `GOLD_V2_18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY_REPORT.md`

Reference summaries from 18K through 18Q may be read only for safety context.

## Load-smoke checks

18S checks:

- 18R status is the expected 18R success status
- 18R human_review_packet_ready is true
- 18R decision_made is false
- 18R approval_granted is false
- 18R total STOP rows is zero
- 18R packet checks have zero STOP rows
- 18R safety matrix has zero STOP rows
- packet index contains all generated packet outputs
- every packet index file exists under the 18R output folder
- human-review packet markdown loads and is non-empty
- markdown contains audit-only language and no approval language
- manual decision questions load and remain `NO_SCRIPT_DECISION`
- blocked actions load and remain `BLOCKED`
- 18R next gates keep source recovery, source finalization, live, and final signal blocked
- all reference summaries keep source recovery, identity finalization, identity recovered, ledger source-of-truth, OHLC replay, live/final, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord false

## Output folder

`FX_OUTPUTS/gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only`

## Outputs

- `GOLD_V2_18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json`
- `gold_v2_18s_input_audit.csv`
- `gold_v2_18s_load_checks.csv`
- `gold_v2_18s_packet_file_audit.csv`
- `gold_v2_18s_markdown_audit.csv`
- `gold_v2_18s_manual_question_audit.csv`
- `gold_v2_18s_blocked_action_audit.csv`
- `gold_v2_18s_required_next_gates.csv`
- `gold_v2_18s_stop_conditions.csv`
- `gold_v2_18s_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that the 18R packet outputs loaded and remained audit-only. It is not a decision, not an approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY`

18T may inspect the human-review packet content more deeply. 18T must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

## BAT execution order

1. Confirm 18R outputs exist.
2. Run `scripts\gold_v2_runtime\bat\18S_AUDIT_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY.bat`.
3. Review load checks, packet file audit, markdown audit, manual question audit, blocked action audit, safety matrix, summary, and report.

## Stop conditions

18S stops if required inputs are missing, 18R did not pass, 18R made a decision or granted approval, any upstream STOP row is present, packet files are missing, markdown is empty or suggests approval, manual questions are not manual-only, blocked actions are not blocked, forbidden gates are allowed, any forbidden safety flag is true, or any output is treated as approval or source-of-truth acceptance.

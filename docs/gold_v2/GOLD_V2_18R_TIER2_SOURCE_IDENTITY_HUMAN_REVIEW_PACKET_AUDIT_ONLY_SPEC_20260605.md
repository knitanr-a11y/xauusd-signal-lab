# GOLD V2 18R TIER2 source identity human review packet audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY`
Mode: audit-only

## Purpose

18R formats the 18Q human-review decision plan into a human-review packet.

18R is not an approval step and must not make a decision. It only organizes the checklist, required evidence, blocked actions, and manual-review prompts into packet outputs.

18R must not promote the dry-run candidate identity ledger to source-of-truth. It must not execute source recovery, finalize source identity, recover source identity, implement live/final evaluator behavior, replay OHLC, send Discord notifications, send NO_SIGNAL Discord notifications, place MT5 orders, call AI APIs, or call live hooks.

## Upstream requirements

18R must stop unless 18Q summary status is:

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18R must also stop unless 18Q decision planning is ready, no decision or approval was made, all 18Q STOP rows are zero, and all forbidden safety flags remain false.

## Inputs

18Q outputs from:

`FX_OUTPUTS/gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only`

- `gold_v2_18q_tier2_source_identity_human_review_decision_planning_summary.json`
- `gold_v2_18q_input_audit.csv`
- `gold_v2_18q_planning_checks.csv`
- `gold_v2_18q_decision_checklist.csv`
- `gold_v2_18q_required_evidence_for_decision.csv`
- `gold_v2_18q_actions_still_blocked.csv`
- `gold_v2_18q_required_next_gates.csv`
- `gold_v2_18q_stop_conditions.csv`
- `gold_v2_18q_safety_matrix.csv`
- `GOLD_V2_18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY_REPORT.md`

Reference summaries from 18K, 18L, 18M, 18N, 18O, and 18P may be read only for packet context.

## Packet checks

18R checks:

- 18Q status is the expected 18Q success status
- 18Q decision planning is ready
- 18Q decision_made is false
- 18Q approval_granted is false
- 18Q total STOP rows is zero
- 18Q planning checks have zero STOP rows
- 18Q safety matrix has zero STOP rows
- decision checklist contains required BLOCKING items
- required evidence includes 18K, 18L, 18M, 18N, and 18O
- blocked actions include source recovery, source identity finalization, live evaluator, final signal, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord
- 18Q next gates keep source recovery, source finalization, live, and final signal blocked
- all reference summaries keep source recovery, identity finalization, identity recovered, ledger source-of-truth, OHLC replay, live/final, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord false

## Output folder

`FX_OUTPUTS/gold_v2_18r_tier2_source_identity_human_review_packet_audit_only`

## Outputs

- `GOLD_V2_18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY_REPORT.md`
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

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that a human-review packet was formatted. It is not a decision, not an approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY`

18S may validate that the human-review packet outputs load and still keep all forbidden gates blocked. 18S must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

## BAT execution order

1. Confirm 18Q outputs exist.
2. Run `scripts\gold_v2_runtime\bat\18R_AUDIT_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY.bat`.
3. Review packet checks, packet index, packet markdown, manual decision questions, blocked actions, safety matrix, summary, and report.

## Stop conditions

18R stops if required inputs are missing, 18Q did not pass, 18Q made a decision or granted approval, any upstream STOP row is present, packet items are missing, required evidence is incomplete, forbidden gates are allowed, any forbidden safety flag is true, or any output is treated as approval or source-of-truth acceptance.

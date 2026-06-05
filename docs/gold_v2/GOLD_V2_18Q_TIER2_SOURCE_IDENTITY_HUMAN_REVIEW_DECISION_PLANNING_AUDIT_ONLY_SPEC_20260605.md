# GOLD V2 18Q TIER2 source identity human review decision planning audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY`
Mode: audit-only

## Purpose

18Q creates a human-review decision planning checklist from the 18P readiness package.

18Q is not an approval step and must not make the decision itself. It only prepares a decision checklist, required evidence list, and explicit blocked actions for a later human review gate.

18Q must not promote the dry-run candidate identity ledger to source-of-truth. It must not execute source recovery, finalize source identity, recover source identity, implement live/final evaluator behavior, replay OHLC, send Discord notifications, send NO_SIGNAL Discord notifications, place MT5 orders, call AI APIs, or call live hooks.

## Upstream requirements

18Q must stop unless 18P summary status is:

`TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

18Q must also stop unless the 18P readiness package was prepared, all 18P STOP rows are zero, all evidence steps are packaged, and all forbidden safety flags remain false.

## Inputs

18P outputs from:

`FX_OUTPUTS/gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only`

- `gold_v2_18p_tier2_source_identity_dry_run_readiness_package_summary.json`
- `gold_v2_18p_input_audit.csv`
- `gold_v2_18p_readiness_checks.csv`
- `gold_v2_18p_evidence_manifest.csv`
- `gold_v2_18p_open_blockers_for_human_review.csv`
- `gold_v2_18p_human_review_packet.csv`
- `gold_v2_18p_required_next_gates.csv`
- `gold_v2_18p_stop_conditions.csv`
- `gold_v2_18p_safety_matrix.csv`
- `GOLD_V2_18P_TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md`

Reference summaries from 18K, 18L, 18M, 18N, and 18O are read only for checklist context.

## Planning checks

18Q checks:

- 18P status is the expected 18P success status
- 18P readiness package was prepared
- 18P total STOP rows is zero
- 18P readiness checks have zero STOP rows
- 18P safety matrix has zero STOP rows
- evidence manifest includes 18K, 18L, 18M, 18N, and 18O
- open blockers are present and remain unresolved
- human review packet exists and contains required blocking items
- 18P next gates keep source recovery, source finalization, live, and final signal blocked
- all reference summaries keep source recovery, identity finalization, identity recovered, ledger source-of-truth, OHLC replay, live/final, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord false

## Output folder

`FX_OUTPUTS/gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only`

## Outputs

- `GOLD_V2_18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY_REPORT.md`
- `gold_v2_18q_tier2_source_identity_human_review_decision_planning_summary.json`
- `gold_v2_18q_input_audit.csv`
- `gold_v2_18q_planning_checks.csv`
- `gold_v2_18q_decision_checklist.csv`
- `gold_v2_18q_required_evidence_for_decision.csv`
- `gold_v2_18q_actions_still_blocked.csv`
- `gold_v2_18q_required_next_gates.csv`
- `gold_v2_18q_stop_conditions.csv`
- `gold_v2_18q_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that a human-review decision checklist was prepared. It is not a decision, not an approval, not source recovery, not source identity finalization, not source-of-truth acceptance, not live readiness, and not final signal readiness.

## Required next gate

`18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY`

18R may format the human review packet for manual review. 18R must still not execute source recovery, finalize source identity, enable live/final behavior, send Discord/MT5 actions, call AI APIs, call live hooks, or notify Discord on NO_SIGNAL.

## BAT execution order

1. Confirm 18P outputs exist.
2. Run `scripts\gold_v2_runtime\bat\18Q_AUDIT_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY.bat`.
3. Review planning checks, decision checklist, required evidence, blocked actions, safety matrix, summary, and report.

## Stop conditions

18Q stops if required inputs are missing, 18P did not pass, any upstream STOP row is present, evidence manifest is incomplete, blocking items are missing, forbidden gates are allowed, any forbidden safety flag is true, or any output is treated as an approval or source-of-truth acceptance.

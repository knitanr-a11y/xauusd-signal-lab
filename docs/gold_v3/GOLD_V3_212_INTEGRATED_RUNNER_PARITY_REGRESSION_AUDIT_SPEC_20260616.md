# GOLD V3 Stage212 Integrated Runner Parity and Regression Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage212 compares split-stage dry-run outputs with the Stage211 integrated OHLC runner output.

The goal is to ensure the integrated runner has not changed detector behavior or writer policy.

## Comparison policy

- If latest closed timestamps are the same, final route must match.
- If Stage211 is newer because OHLC was refreshed, classify as input freshness drift, not a blocker.
- On overlapping tail rows, detector routes and feature values must match exactly.
- Writer policy must remain consistent.
- NO_SIGNAL must not create signal/notification append rows.
- NO_SIGNAL must increment counter.

## Inputs

- Stage200 decision and tail96
- Stage209 decision and latest_state
- Stage210 decision and write plan
- Stage211 decision, integrated tail96, latest_state, and write plan

## Outputs

- `gold_v3_212_source_presence.csv`
- `gold_v3_212_latest_summary_comparison.csv`
- `gold_v3_212_freshness_classification.csv`
- `gold_v3_212_tail_overlap_rows.csv`
- `gold_v3_212_tail_overlap_parity_checks.csv`
- `gold_v3_212_writer_policy_parity.csv`
- `gold_v3_212_integrated_state_parity.csv`
- `gold_v3_212_integrated_runner_parity_plan.md`
- `gold_v3_212_summary.json`
- `gold_v3_212_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- dry-run only
- no live retention file mutation
- no source CSV mutation
- no actual import
- no execution
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify

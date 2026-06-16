# GOLD V3 Stage214 Idempotent Writer and Duplicate Signal ID Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage214 defines repeat-safe writer behavior before any live writer is enabled.

It verifies that repeated evaluations do not create duplicate rows or duplicate counter increments.

## Scope

- signal ledger duplicate signal_id behavior
- notification event duplicate behavior
- NO_SIGNAL counter duplicate behavior for the same closed bar
- latest_state overwrite behavior
- debug tail snapshot replacement behavior

## Inputs

- Stage204 enriched trade signal sample
- Stage208 signal_id map sample
- Stage211 latest_state integrated preview
- Stage213 readiness decision

## Outputs

- `gold_v3_214_signal_sample_with_short_id.csv`
- `gold_v3_214_idempotency_rules.csv`
- `gold_v3_214_signal_duplicate_simulation.csv`
- `gold_v3_214_notification_duplicate_simulation.csv`
- `gold_v3_214_no_signal_counter_duplicate_simulation.csv`
- `gold_v3_214_latest_state_snapshot_idempotency.csv`
- `gold_v3_214_writer_decision_contract.csv`
- `gold_v3_214_validation_checks.csv`
- `gold_v3_214_idempotent_writer_plan.md`
- `gold_v3_214_summary.json`
- `gold_v3_214_decision.csv`
- `paste_me.txt`

## Required behavior

- new signal_id: append preview
- repeated signal_id: skip duplicate
- new notification event key: append preview only
- repeated notification event key: skip duplicate
- first NO_SIGNAL closed-bar key: increment counter
- repeated NO_SIGNAL closed-bar key: skip counter increment
- latest_state: overwrite
- debug tail: replace rolling snapshot

## Guardrails

- audit-only
- dry-run only
- no production retention file mutation
- no source CSV mutation
- no actual import
- no execution
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify

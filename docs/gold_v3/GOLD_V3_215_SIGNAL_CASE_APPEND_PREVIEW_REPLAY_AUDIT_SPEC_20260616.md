# GOLD V3 Stage215 SIGNAL Case Append Preview Replay Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage215 replays a known SIGNAL sample and validates the SIGNAL-side append preview shape.

This is needed because recent integrated cycles were NO_SIGNAL, so SIGNAL append shape must be checked using a replay sample.

## Inputs

- Stage204 enriched trade signal sample
- Stage208 signal_id map sample
- Stage214 repeat-safe writer decision

## Outputs

- `gold_v3_215_latest_state_signal_replay_preview.json`
- `gold_v3_215_trade_signal_append_replay_preview.csv`
- `gold_v3_215_notification_append_replay_preview.csv`
- `gold_v3_215_no_signal_counter_replay_preview.csv`
- `gold_v3_215_health_rollup_signal_replay_preview.csv`
- `gold_v3_215_duplicate_key_replay_preview.csv`
- `gold_v3_215_validation_checks.csv`
- `gold_v3_215_signal_case_replay_plan.md`
- `gold_v3_215_summary.json`
- `gold_v3_215_decision.csv`
- `paste_me.txt`

## Required behavior

- SIGNAL replay latest_state contains signal_id and short_signal_id
- trade_signal append preview has one row
- notification append preview has one row
- NO_SIGNAL counter preview has zero rows
- notification send action remains NO_SEND_AUDIT_ONLY
- duplicate keys align with Stage214 rules

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

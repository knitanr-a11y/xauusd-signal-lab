# GOLD V3 Stage208 Signal ID Embedding Contract Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage208 fixes signal identity across the long-retention ledgers and future execution import.

It defines:

- full signal_id
- short_signal_id
- signal_id_map
- notification sample embedding
- future execution comment embedding
- validation checks

## ID design

`signal_id` is the full canonical key.

`short_signal_id` is a compact deterministic key generated from the full key.

The short key uses:

- prefix: G3S
- hash: blake2s hex prefix

## Embedding locations

- trade_signal_ledger.csv stores signal_id and short_signal_id
- notification_events_rolling_30d.csv stores both ids
- future execution comment stores short_signal_id
- actual_execution_ledger stores extracted short_signal_id
- signal_id_map resolves short_signal_id back to signal_id
- execution_reconciliation_ledger uses full signal_id

## Outputs

- `gold_v3_208_signal_id_contract_sample.csv`
- `gold_v3_208_signal_id_map_sample.csv`
- `gold_v3_208_embedding_locations.csv`
- `gold_v3_208_notification_event_with_signal_id_sample.csv`
- `gold_v3_208_execution_comment_contract_sample.csv`
- `gold_v3_208_signal_id_validation_checks.csv`
- `gold_v3_208_signal_id_embedding_contract.md`
- `gold_v3_208_summary.json`
- `gold_v3_208_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- dry-run only
- no source CSV mutation
- no actual export import
- no execution
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify

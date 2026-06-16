# GOLD V3 Stage207 Actual Execution Import Contract Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage207 defines the future actual execution import contract.

It does not import real order history yet.

It defines:

- expected MT5 account-history export fields
- field mapping into canonical actual execution ledger fields
- preferred matching keys
- fallback matching keys
- unmatched signal handling
- orphan execution handling

## Matching priority

1. Prefer `signal_id`.

Future order comments or export rows should carry signal_id whenever possible.

2. If signal_id is missing, fallback matching can use:

- symbol
- direction
- actual open time close to signal entry time
- actual entry price close to intended entry price
- optional magic number or comment

3. If a signal has no actual execution match:

- create unmatched_signal row

4. If an actual execution has no signal match:

- create orphan_execution row

## Safety

- audit-only
- dry-run only
- no actual order export import
- no MT5 order placed
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify
- raw account id must not be stored in shared artifacts

## Outputs

- `gold_v3_207_actual_execution_import_expected_schema.csv`
- `gold_v3_207_actual_execution_import_field_mapping.csv`
- `gold_v3_207_actual_execution_import_sample_no_real_orders.csv`
- `gold_v3_207_signal_actual_execution_join_contract_sample.csv`
- `gold_v3_207_unmatched_signal_contract_sample.csv`
- `gold_v3_207_orphan_execution_contract_schema.csv`
- `gold_v3_207_import_validation_rules.csv`
- `gold_v3_207_actual_execution_import_contract.md`
- `gold_v3_207_summary.json`
- `gold_v3_207_decision.csv`
- `paste_me.txt`

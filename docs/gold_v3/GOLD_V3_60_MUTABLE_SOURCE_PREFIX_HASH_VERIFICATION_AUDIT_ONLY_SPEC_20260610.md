# GOLD V3 60 mutable source prefix-hash verification audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_60_MUTABLE_SOURCE_PREFIX_HASH_VERIFICATION_SPEC_READY_AUDIT_ONLY`

## Purpose

Verify the Stage59 mutable source candle prefix-hash baseline.

Stage60 recomputes SHA-256 over the same bounded prefix for each mutable source candle:

- `m5_csv`
- `m15_csv`
- `h4_csv`

Appended rows after `checkpoint_row_count` are allowed. Any change inside the frozen prefix is BLOCKED.

Stage60 is audit-only. It does **not** execute trades, refresh checkpoints, send notifications, or enable live trading.

## Required upstream artifacts

- Stage59 prefix hash summary READY
- Stage59 mutable source prefix hash snapshot CSV

## Non-negotiable safety boundaries

- GOLD V3 remains audit-only.
- No MT5 orders.
- No MT5 execution BAT.
- No Discord live notification.
- No AI API call.
- No live hook.
- No final signal.
- No candidate pool mutation.
- No high-vol profile demotion/removal.
- No GOLD V2 / old GOLD / DISC8.
- No Stage41 feature-only trading source.

## Verification rules

For each mutable source candle:

1. file exists
2. current row count >= checkpoint row count
3. prefix rows used == checkpoint row count
4. recomputed prefix SHA-256 == Stage59 prefix SHA-256
5. appended rows after checkpoint row count are allowed

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\60_mutable_source_prefix_hash_verification_audit_only`

Files:

- `gold_v3_60_prefix_hash_verification_matrix.csv`
- `gold_v3_60_validation_matrix.csv`
- `gold_v3_60_prefix_hash_verification_summary.json`
- `gold_v3_60_PASTE_ME_PREFIX_HASH_VERIFY_SUMMARY.txt`
- `GOLD_V3_60_REPORT.md`

## Success condition

Stage60 READY means:

- Stage59 prefix-hash baseline is present and READY.
- All mutable sources still contain at least the frozen prefix.
- All recomputed prefix hashes match the Stage59 baseline.
- Appended rows, if any, are outside the frozen replay prefix.

READY does not approve live trading.

## Next stage

Stage61 should prepare a frozen audit package / human review packet, still audit-only, unless explicitly directed otherwise.

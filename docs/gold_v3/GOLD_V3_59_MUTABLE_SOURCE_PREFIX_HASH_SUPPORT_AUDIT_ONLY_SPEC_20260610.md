# GOLD V3 59 mutable source prefix-hash support audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_59_MUTABLE_SOURCE_PREFIX_HASH_SUPPORT_SPEC_READY_AUDIT_ONLY`

## Purpose

Add prefix-hash support for mutable source candle files used by bounded checkpoint replay.

Stage59 creates a new baseline snapshot for `m5_csv`, `m15_csv`, and `h4_csv` by hashing only:

- the CSV header line
- the first `checkpoint_row_count` data rows recorded by Stage57

This allows later stages to verify that appended source candle rows did not alter the frozen replay prefix.

Stage59 is audit-only. It does **not** refresh Stage54, does **not** rerun trading logic, and does **not** enable live trading.

## Required upstream artifacts

- Stage57 bounded replay summary READY
- Stage57 mutable source window freeze CSV
- Stage58 bounded replay summary READY
- Stage58 mutable source bounded window CSV

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

## Prefix-hash definition

For a CSV with `checkpoint_row_count = N`, compute SHA-256 over the raw bytes of:

1. header line
2. first N data lines

The hash is byte-level over the file's current newline and encoding bytes. Rows after N are excluded.

## Important limitation

Stage59 creates the first prefix-hash baseline. It cannot prove that the prefix matched at Stage54 time because Stage54 did not store prefix hashes. It only makes future prefix verification possible from Stage59 onward.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\59_mutable_source_prefix_hash_support_audit_only`

Files:

- `gold_v3_59_mutable_source_prefix_hash_snapshot.csv`
- `gold_v3_59_prefix_hash_validation_matrix.csv`
- `gold_v3_59_prefix_hash_summary.json`
- `gold_v3_59_PASTE_ME_PREFIX_HASH_SUMMARY.txt`
- `GOLD_V3_59_REPORT.md`

## Success condition

Stage59 READY means:

- Stage57 and Stage58 are READY.
- All mutable source candle files exist.
- Current row count is at least checkpoint row count.
- Prefix hash was computed for all mutable sources.
- No live trading capability was enabled.

READY does not approve live trading.

## Next stage

Stage60 should run prefix-hash verification after a short delay or after additional candle append. It must verify that the Stage59 prefix hashes still match while allowing appended rows beyond the frozen replay window.

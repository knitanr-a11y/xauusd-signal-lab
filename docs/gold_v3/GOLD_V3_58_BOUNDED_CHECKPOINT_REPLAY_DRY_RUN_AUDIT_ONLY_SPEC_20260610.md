# GOLD V3 58 bounded checkpoint replay dry run audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_58_BOUNDED_CHECKPOINT_REPLAY_DRY_RUN_SPEC_READY_AUDIT_ONLY`

## Purpose

Run an audit-only bounded checkpoint replay dry run using the Stage57 `B_BOUNDED_REPLAY_WINDOW_FREEZE` contract.

Stage58 verifies that:

- mutable source candles are currently at least as long as the checkpoint row count
- bounded replay uses only rows `1..checkpoint_row_count`
- appended rows after checkpoint are excluded from checkpoint parity
- immutable state artifacts remain strict hash/row-count matched
- Stage55 strict full-file replay may remain BLOCKED while bounded replay can be READY

Stage58 does **not** execute trades, refresh checkpoints, send notifications, or enable live trading.

## Required upstream artifacts

- Stage54 checkpoint summary READY
- Stage54 source artifact hashes CSV
- Stage55 replay dry-run summary BLOCKED
- Stage56 drift policy summary READY
- Stage57 bounded replay summary READY
- Stage57 bounded replay window contract CSV
- Stage57 mutable source window freeze CSV

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

## Bounded replay rules

For mutable source candles (`m5_csv`, `m15_csv`, `h4_csv`):

- current row count must be greater than or equal to checkpoint row count
- bounded replay row count is checkpoint row count
- outside frozen window rows are ignored for checkpoint parity
- if current row count is below checkpoint row count, BLOCK

For immutable state artifacts:

- current hash must match checkpoint hash
- current row count must match checkpoint row count when applicable
- any mismatch is BLOCK

Important limitation:

Stage54 did not store prefix hashes for source candle CSVs. Therefore Stage58 cannot prove byte-level prefix identity for mutable sources. It proves only bounded row-count availability plus immutable state stability. Prefix-hash support can be added in a later audit stage.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\58_bounded_checkpoint_replay_dry_run_audit_only`

Files:

- `gold_v3_58_bounded_replay_check_matrix.csv`
- `gold_v3_58_mutable_source_bounded_window.csv`
- `gold_v3_58_immutable_state_recheck.csv`
- `gold_v3_58_validation_matrix.csv`
- `gold_v3_58_bounded_replay_summary.json`
- `gold_v3_58_PASTE_ME_BOUNDED_REPLAY_DRY_RUN_SUMMARY.txt`
- `GOLD_V3_58_REPORT.md`

## Success condition

Stage58 READY means:

- Stage57 bounded contract is READY.
- All mutable source candles satisfy current row count >= checkpoint row count.
- All immutable state artifacts remain strict-stable.
- Appended mutable rows are excluded from checkpoint parity.
- Stage55 strict full-file replay may still be BLOCKED by design.

READY does not approve live trading.

## Next stage

Stage59 should decide whether to add prefix-hash snapshot support for mutable candles or prepare a frozen audit package for human review. It must remain audit-only unless explicitly approved otherwise.

# GOLD V3 57 bounded replay window freeze decision audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_57_BOUNDED_REPLAY_WINDOW_FREEZE_DECISION_SPEC_READY_AUDIT_ONLY`

## Purpose

Record the human decision to use **B: bounded replay window freeze** after Stage55 strict replay detected mutable source candle drift and Stage56 classified it as `MUTABLE_SOURCE_ADVANCED_APPEND_LIKELY`.

Stage57 freezes replay verification for mutable source candle files to the Stage54 checkpoint row-count/time-anchor boundary. Rows appended after the checkpoint are not deleted and are not used for replay parity of the frozen checkpoint.

Stage57 does **not** refresh the checkpoint, does **not** run trading logic, and does **not** enable live trading.

## Human decision

Decision: `B_BOUNDED_REPLAY_WINDOW_FREEZE`

Meaning:

- Keep Stage54 checkpoint as the audit replay boundary.
- Do not rewrite or truncate live/source candle CSV files.
- Do not update Stage54 hashes.
- For mutable source candles, verify replay only up to checkpoint row count and checkpoint anchor.
- Immutable state artifacts remain strict hash/row-count checked.

## Required upstream artifacts

- Stage54 checkpoint summary READY
- Stage54 source artifact hashes CSV
- Stage54 restart plan CSV
- Stage55 replay dry-run summary BLOCKED
- Stage55 hash recheck CSV
- Stage56 policy summary READY
- Stage56 drift policy matrix CSV

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

## Contract rules

Artifact roles:

- `mutable_source_candle`: `m5_csv`, `m15_csv`, `h4_csv`
- `immutable_state_artifact`: all Stage state/ledger outputs

For mutable source candles:

- current row count may be greater than checkpoint row count
- bounded replay uses `checkpoint_row_count`
- any rows after checkpoint row count are `outside_frozen_replay_window`
- source rewrite/truncation remains BLOCKER

For immutable state artifacts:

- any hash mismatch remains BLOCKER
- any row count mismatch remains BLOCKER

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\57_bounded_replay_window_freeze_decision_audit_only`

Files:

- `gold_v3_57_bounded_replay_window_contract.csv`
- `gold_v3_57_mutable_source_window_freeze.csv`
- `gold_v3_57_validation_matrix.csv`
- `gold_v3_57_bounded_replay_summary.json`
- `gold_v3_57_PASTE_ME_BOUNDED_REPLAY_SUMMARY.txt`
- `GOLD_V3_57_REPORT.md`

## Success condition

Stage57 READY means:

- Human decision B is recorded.
- Stage56 policy is READY.
- No immutable state drift blockers exist.
- No mutable source rewrite/truncation blockers exist.
- Bounded window contract is written for mutable source candles.
- Stage55 strict replay remains not-ready, intentionally, because Stage55 was strict full-file hash replay.

## Next stage

Stage58 should implement a bounded checkpoint replay dry-run that applies the Stage57 contract. It must remain audit-only and must not enable live trading.

# GOLD V3 55 replay-from-checkpoint dry run audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_55_REPLAY_FROM_CHECKPOINT_DRY_RUN_SPEC_READY_AUDIT_ONLY`

## Purpose

Run an audit-only dry-run validation from the Stage54 restart/replay checkpoint.

Stage55 does not re-run Stage50/51/52/53 trading logic. It only verifies that the existing checkpoint, artifact hashes, restart anchors, and count continuity remain valid.

## Frozen upstream contract

Stage55 must preserve:

- GOLD V3 audit-only
- closed H4 asof only
- OPEN asof prohibited
- full Stage45 base + HV sibling pool retained
- no manual candidate demotion/removal
- no contract mutation
- strict rolling health gate unchanged
- Stage52 selected trades only
- Stage53 M5 adjudication parity already zero

## Required upstream artifacts

- Stage54 checkpoint summary READY
- Stage54 replay checkpoint state CSV
- Stage54 source artifact hashes CSV
- Stage54 restart plan CSV
- Stage54 validation matrix CSV

## Non-negotiable safety boundaries

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

## Dry-run behavior

Stage55 verifies:

1. Stage54 checkpoint READY.
2. All Stage54 safety flags remain OFF.
3. Every artifact path listed in `gold_v3_54_source_artifact_hashes.csv` still exists.
4. Current SHA-256 hash equals the checkpointed SHA-256 hash.
5. Current CSV row count equals the checkpointed CSV row count when applicable.
6. Restart plan has exactly 8 ordered steps.
7. Restart anchors are non-empty.
8. Stage51/52/53 counts recorded in Stage54 summary remain internally consistent.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\55_replay_from_checkpoint_dry_run_audit_only`

Files:

- `gold_v3_55_hash_recheck.csv`
- `gold_v3_55_restart_anchor_recheck.csv`
- `gold_v3_55_replay_anchor_check_matrix.csv`
- `gold_v3_55_validation_matrix.csv`
- `gold_v3_55_replay_dry_run_summary.json`
- `gold_v3_55_PASTE_ME_REPLAY_DRY_RUN_SUMMARY.txt`
- `GOLD_V3_55_REPORT.md`

## Interpretation

READY means the frozen checkpoint is still reproducible from existing artifacts.
It does not approve live trading.

## Next stage

Stage56 should be a human decision checkpoint: whether to continue deeper audit-only robustness checks or stop at a frozen shadow-readiness package. It must not enable live trading without explicit approval.

# GOLD V3 54 restart/replay checkpoint state audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_SPEC_READY_AUDIT_ONLY`

## Purpose

Build an audit-only restart/replay checkpoint state for the frozen GOLD V3 state chain.

Stage54 records:

- source candle file hashes
- upstream state/ledger artifact hashes
- final processed M15/selected/closed timestamps
- restart anchors
- deterministic replay order
- validation that Stage49-53 state outputs are READY and internally consistent

Stage54 does **not** implement live trading, does **not** send signals, and does **not** change candidate or gate logic.

## Frozen upstream contract

Stage54 must preserve:

- `htf_asof = closed`
- OPEN asof prohibited
- full Stage45 base + HV sibling candidate pool retained
- no manual candidate demotion/removal
- strict rolling health gate unchanged
- all candidates virtually monitored
- selected trades from Stage52 only
- M5 adjudication parity from Stage53

## Required upstream artifacts

- Stage49 state schema summary READY
- Stage50 H4/q70 state builder summary READY
- Stage51 virtual opportunity ledger summary READY
- Stage52 health gate selection summary READY
- Stage53 shadow adjudication summary READY
- source candles:
  - `goldsharp_m5.csv`
  - `goldsharp_m15.csv`
  - `goldsharp_h4.csv`

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

## Restart/replay contract

A later audit-only replay must process artifacts in this order:

1. H4 closed readiness state
2. rolling prior-60D q70 state
3. full-candidate virtual opportunity ledger
4. health gate state
5. rank-dedup selection ledger
6. pending shadow trade ledger
7. closed shadow trade ledger
8. checkpoint state

Restart anchors:

- `last_virtual_opportunity_m15_time`
- `last_selection_m15_time`
- `last_pending_entry_time`
- `last_closed_exit_time`
- `source_file_hashes_json`
- `state_artifact_hashes_json`

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\54_restart_replay_checkpoint_state_audit_only`

Files:

- `gold_v3_54_replay_checkpoint_state.csv`
- `gold_v3_54_source_artifact_hashes.csv`
- `gold_v3_54_restart_plan.csv`
- `gold_v3_54_validation_matrix.csv`
- `gold_v3_54_checkpoint_summary.json`
- `gold_v3_54_PASTE_ME_CHECKPOINT_SUMMARY.txt`
- `GOLD_V3_54_REPORT.md`

## Validation

Stage54 validates:

1. Stage49/50/51/52/53 summaries are present and READY.
2. Safety flags remain OFF across Stage49-53.
3. No upstream contract mutation or manual candidate demotion/removal exists.
4. Stage51 opportunity count matches Stage52 input opportunity count.
5. Stage52 selected trade count matches Stage53 pending/closed trade counts.
6. Stage53 adjudication parity mismatch is zero.
7. All source and artifact hashes are non-empty.
8. Replay order is frozen.

## Interpretation

READY means a deterministic audit-only restart/replay checkpoint has been written.
It does not approve live trading.

## Next stage

Stage55 should run an audit-only replay-from-checkpoint dry run and confirm hash/count anchors without enabling MT5/Discord/live/final signal.

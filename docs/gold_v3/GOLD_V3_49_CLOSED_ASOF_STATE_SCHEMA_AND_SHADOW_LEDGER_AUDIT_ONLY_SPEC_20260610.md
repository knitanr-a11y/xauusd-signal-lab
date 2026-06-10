# GOLD V3 49 closed-asof state schema and shadow ledger audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_SPEC_READY_AUDIT_ONLY`

## Purpose

Define the persistent state schemas required before the Stage46/47 frozen contract can be converted into any audit-only shadow evaluator.

Stage49 does **not** implement live trading, does **not** send signals, and does **not** change candidate selection logic.
It only freezes schema contracts for future audit-only state management.

## Upstream contract

Stage49 must preserve the Stage46/47 contract:

- `htf_asof = closed`
- OPEN asof prohibited
- full Stage45 base + HV sibling candidate pool retained
- high-vol profiles retained:
  - `HV_TP180_SL70_H128`
  - `HV_TP200_SL80_H128`
  - `HV_TP220_SL90_H128`
- no manual candidate demotion/removal
- selection by strict rolling health gate only
- all candidates virtually monitored

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

## State schemas to freeze

Stage49 freezes schema definitions for these audit-only artifacts:

1. `h4_closed_readiness_state`
   - Confirms latest H4 row is closed and safe to use.
2. `rolling_prior_60d_q70_state`
   - Stores prior-only ATR28 q70 high-vol threshold for each M15 decision time.
3. `virtual_opportunity_ledger`
   - Stores every base/HV candidate opportunity whether selected or not.
4. `health_gate_state`
   - Stores per-candidate rolling PF/loss-streak eligibility state.
5. `rank_dedup_selection_ledger`
   - Stores deterministic candidate priority and selected candidate per M15 timestamp.
6. `pending_shadow_trade_ledger`
   - Stores audit-only pending trades waiting for M5 TP/SL/timeout adjudication.
7. `closed_shadow_trade_ledger`
   - Stores completed audit-only outcome records.
8. `replay_checkpoint_state`
   - Stores restart/replay anchors and source file hashes.

## Required outputs

Default output folder:

`Files\FX_OUTPUTS\gold_v3\49_closed_asof_state_schema_and_shadow_ledger_audit_only`

Files:

- `gold_v3_49_state_artifact_manifest.csv`
- `gold_v3_49_shadow_ledger_schema.csv`
- `gold_v3_49_state_transition_matrix.csv`
- `gold_v3_49_empty_schema_templates/`
- `gold_v3_49_validation_matrix.csv`
- `gold_v3_49_state_schema_summary.json`
- `gold_v3_49_PASTE_ME_STATE_SCHEMA_SUMMARY.txt`
- `GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_AUDIT_ONLY_REPORT.md`

## Stop conditions

Stop if:

- Stage46 contract is missing or not READY
- Stage47 forward audit summary is missing or not READY
- Stage48 gap summary is missing or not report-ready
- any upstream output indicates candidate mutation
- any upstream output indicates manual demotion/removal
- any upstream output allows OPEN asof
- any live/MT5/Discord/final signal flag is enabled

## Interpretation

A READY status means the audit-only state/ledger schema has been frozen.
It does not mean a shadow evaluator has been implemented, and it does not approve live trading.

## Next stage

Stage50 should implement an audit-only H4 closed-row readiness checker and rolling prior-60D q70 state builder using the Stage49 schema.

# GOLD V3 51 full-candidate virtual opportunity ledger builder audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_51_FULL_CANDIDATE_VIRTUAL_OPPORTUNITY_LEDGER_BUILDER_SPEC_READY_AUDIT_ONLY`

## Purpose

Build the full-candidate virtual opportunity ledger required for audit-only shadow monitoring.

Stage51 uses the Stage50 prior-60D q70 state and the frozen Stage46/47 candidate pool contract to generate every base/HV candidate opportunity, whether later selected or not.

Stage51 does **not** implement a live evaluator, does **not** send signals, and does **not** change candidate or gate logic.

## Frozen upstream contract

Stage51 must preserve:

- `htf_asof = closed`
- OPEN asof prohibited
- full Stage45 base + HV sibling candidate pool retained
- high-vol profiles retained:
  - `HV_TP180_SL70_H128`
  - `HV_TP200_SL80_H128`
  - `HV_TP220_SL90_H128`
- no manual candidate demotion/removal
- strict rolling health gate unchanged
- all candidates virtually monitored

## Required upstream artifacts

- Stage46 contract output READY
- Stage47 forward audit output READY
- Stage49 state schema output READY
- Stage50 state builder output READY
- Stage47 replay Stage45 opportunity ledger for parity comparison:
  - `stage47_replay/gold_v3_45_all_candidate_opportunity_ledger.csv`

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

## Builder behavior

1. Read M15/M5/H4 candles.
2. Read Stage50 `rolling_prior_60d_q70_state`.
3. Prepare closed-asof H4 feature values using `h4_open_time + 4h`.
4. Inject Stage50 `high_vol_pass` into the M15 working frame as `is_high_vol`.
5. Reuse Stage45 candidate definitions and filters.
6. Generate all base and HV sibling candidate opportunities.
7. Evaluate opportunities with M5 TP/SL/timeout using complete horizon only.
8. Write the full virtual opportunity ledger.
9. Compare total and candidate-level counts against Stage47 replay Stage45 ledger.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\51_full_candidate_virtual_opportunity_ledger_builder_audit_only`

Files:

- `gold_v3_51_virtual_opportunity_ledger.csv`
- `gold_v3_51_candidate_count_parity.csv`
- `gold_v3_51_candidate_summary.csv`
- `gold_v3_51_validation_matrix.csv`
- `gold_v3_51_virtual_opportunity_summary.json`
- `gold_v3_51_PASTE_ME_VIRTUAL_OPPORTUNITY_SUMMARY.txt`
- `GOLD_V3_51_REPORT.md`

## Validation

Stage51 validates:

1. Stage46/47/49/50 upstream READY.
2. Stage50 q70 state exists and has `high_vol_pass` values.
3. Candidate pool includes base + HV sibling candidates.
4. No candidate mutation/demotion/removal occurred.
5. Virtual ledger is non-empty.
6. Total count matches Stage47 replay ledger.
7. Candidate-level counts match Stage47 replay ledger.
8. Safety flags remain OFF.

## Interpretation

READY means the virtual opportunity ledger is reproducible and matches the Stage47 replay opportunity ledger.
It does not approve live trading.

## Next stage

Stage52 should build the persistent health gate state and rank-dedup selection ledger from this Stage51 virtual opportunity ledger, still audit-only.

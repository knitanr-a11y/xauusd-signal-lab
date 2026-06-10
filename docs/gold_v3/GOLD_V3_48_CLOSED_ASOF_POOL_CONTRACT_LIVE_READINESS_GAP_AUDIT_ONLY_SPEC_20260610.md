# GOLD V3 48 closed-asof pool contract live-readiness gap audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_SPEC_READY_AUDIT_ONLY`

## Purpose

Audit what is still missing before the frozen Stage46/47 contract can be converted into any live/shadow evaluator.

Stage48 does **not** implement live trading and does **not** change the trading contract.
It only produces a gap matrix.

## Frozen upstream contract

Stage48 must use the Stage46/47 frozen contract as-is:

- HTF asof: `closed`
- OPEN asof: prohibited
- candidate pool: full Stage45 base + HV sibling pool retained
- high-vol profiles retained:
  - `HV_TP180_SL70_H128`
  - `HV_TP200_SL80_H128`
  - `HV_TP220_SL90_H128`
- no manual demotion/removal
- rolling health gate:
  - window 30
  - min_history 20
  - PF threshold 1.1
  - loss streak `< 3`
  - virtual monitoring true

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
- No Stage41 feature-only snapshot as trading source.

## What Stage48 checks

Stage48 checks local readiness gaps across:

1. Input candle availability
2. Closed H4 asof reproducibility
3. M15/M5 time alignment expectations
4. Rolling prior-60D q70 high-vol gate reproducibility
5. Rolling health gate virtual monitoring persistence
6. Rank de-dup / candidate priority reproducibility
7. Open trade horizon adjudication gap for live/shadow audit
8. Safety flags / deployment blockers
9. Required next implementation artifacts

## Expected output status

Stage48 may produce a report-ready status even when live blockers exist:

`GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_REPORT_READY_AUDIT_ONLY`

This means the gap report is ready, not that live trading is ready.

## Outputs

Default output folder:

`Files\FX_OUTPUTS\gold_v3\48_closed_asof_pool_contract_live_readiness_gap_audit_only`

Files:

- `gold_v3_48_input_candle_inventory.csv`
- `gold_v3_48_live_readiness_gap_matrix.csv`
- `gold_v3_48_validation_matrix.csv`
- `gold_v3_48_live_readiness_gap_summary.json`
- `gold_v3_48_PASTE_ME_LIVE_READINESS_GAP_SUMMARY.txt`
- `GOLD_V3_48_CLOSED_ASOF_POOL_CONTRACT_LIVE_READINESS_GAP_AUDIT_ONLY_REPORT.md`

## Stop conditions

Stop if:

- Stage46 contract is missing
- Stage47 forward audit summary is missing
- Stage46/47 status is not READY
- Stage47 says candidate contract was changed
- Stage47 says manual candidate demotion/removal occurred
- Stage47 does not use closed asof

## Interpretation

A PASS in Stage48 means the gap audit ran correctly.
It does not grant live trading permission.
Blocker gaps must be resolved in later audit-only stages before any shadow/live evaluator can be considered.

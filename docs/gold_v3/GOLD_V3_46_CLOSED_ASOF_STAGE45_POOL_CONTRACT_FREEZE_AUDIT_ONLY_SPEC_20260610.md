# GOLD V3 46 closed-asof Stage45 pool contract freeze audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_SPEC_READY_AUDIT_ONLY`

## Purpose

Freeze the Stage45 audit-only contract exactly as validated under closed HTF asof.

This stage does **not** remove, demote, or manually exclude any Stage45 candidate profile.
Candidate selection remains the responsibility of the rolling health gate.

## Hard safety boundaries

- GOLD V3 remains audit-only.
- No MT5 orders.
- No MT5 execution BAT.
- No Discord live notification.
- No AI API call.
- No live hook.
- No final signal.
- No GOLD V2 / old GOLD / DISC8 fallback.
- No Stage41 feature-only trading source.
- OPEN HTF asof is invalid for this contract because H4 candle values are written at close and OPEN mode may use future information.

## Frozen contract

### HTF asof

- `htf_asof = closed`
- `open` mode is not contract-valid.

### Candidate pool

Keep the full Stage45 pool:

- Existing 8 honmei candidates
- High-vol siblings for every honmei candidate
- All high-vol profiles remain in the pool:
  - `HV_TP180_SL70_H128`
  - `HV_TP200_SL80_H128`
  - `HV_TP220_SL90_H128`

No candidate or high-vol TP/SL profile is manually demoted or removed in Stage46.

### High-vol rule

`m15_atr28 >= rolling prior 60D q0.7`

### Rolling health gate

- window: `30`
- min_history: `20`
- pf_threshold: `1.1`
- loss_streak_lt: `3`
- virtual_monitoring: `true`

All candidates are virtually monitored even when not selected.
If a candidate fails the gate, it is temporarily not selected by the gate, not manually removed from the pool.

## Required Stage45 closed result baseline

The Stage45 closed valid baseline from local output is:

- trades: `494`
- win_rate: `66.60%`
- profit_factor: `3.333`
- sum_result_usd: `17006.03`
- max_drawdown_usd: `900.00`
- loss_months: `0`

These are audit result references only. They are not live approval.

## Stage46 local runner behavior

The Stage46 runner reads the existing Stage45 closed output folder and validates:

1. `htf_asof == closed`
2. `audit_only == true`
3. live/MT5/Discord/final signal flags are false
4. the fixed8 + HV siblings strict rolling health gate experiment exists
5. the frozen gate parameters match the above contract
6. high-vol profile names include TP180/SL70, TP200/SL80, and TP220/SL90
7. no manual candidate demotion/removal is introduced by Stage46

Then it writes:

- `gold_v3_46_closed_asof_stage45_pool_contract.json`
- `gold_v3_46_closed_asof_stage45_pool_contract.csv`
- `gold_v3_46_validation_matrix.csv`
- `gold_v3_46_PASTE_ME_CONTRACT_FREEZE_SUMMARY.txt`
- `GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_AUDIT_ONLY_REPORT.md`

## Stop conditions

Stop if:

- Stage45 closed output is missing
- `htf_asof` is not `closed`
- any safety flag indicates live/MT5/Discord/final signal activity
- gate parameters differ from the frozen contract
- the Stage45 strict gate experiment row is missing
- candidate definitions cannot confirm the full HV profile pool

## Next stage

After Stage46 passes, proceed to Stage47 forward audit / local monitoring design, still audit-only.

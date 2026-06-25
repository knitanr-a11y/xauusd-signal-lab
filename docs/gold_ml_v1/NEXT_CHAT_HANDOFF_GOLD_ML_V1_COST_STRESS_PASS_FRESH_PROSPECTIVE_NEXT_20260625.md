# GOLD_ML_V1 Cost-Stress PASS — Fresh Prospective Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_021_COST_STRESS_PASS_FRESH_PROSPECTIVE_IMPLEMENTATION_NEXT_AUDIT_ONLY`

## Verified local result

The user uploaded `UPLOAD_THIS_GOLD_ML_V1.txt` generated at `2026-06-25T19:31:38`.

Verified top-level result:

- exit code: `0`
- run status: `PASS`
- RAW baseline parity checks: `1687`
- frozen candidate stress gate: `PASS=9`, `FAIL=0`
- all frozen nine candidates passed all frozen twelve cost scenarios
- cost-stress error: `NONE`
- no automatic next phase was performed

Machine-readable result record:

`config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`

## Frozen cost grid that passed

- spread multipliers: `1.0`, `1.5`, `2.0`
- fixed slippage points per side: `0`, `5`, `10`, `20`
- Cartesian scenarios: `12`
- same fixed trade membership across scenarios
- candidate gate required every scenario to pass trade count, PF and mean-R conditions

No post-result retuning, grid change, candidate rescue, candidate replacement, removal or relabeling occurred.

## Population contract

`RAW_RECONSTRUCTED` remains the only stressed primary population.

`WARMUP_BRIDGE_EXACT` remains a separate historical exact-core audit:

- `stress_replay_status=NOT_CALCULATED_AUDIT_ONLY`
- `stress_gate_status=NOT_ELIGIBLE_AUDIT_ONLY`
- blocker: `PRE_2023_INDICATOR_STATE_AND_PRICE_FIELDS_UNAVAILABLE_FOR_EXACT_COST_REPLAY`
- never live, promotion, tuning or primary cost-stress input

## One-click workflow state

The cost-stress phase BAT remains:

`scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat`

The user-facing entrypoint remains:

`RUN_GOLD_ML_V1_NEXT.bat`

The current `next_local_action.json` is now `status_only`. The user does not need to rerun cost stress.

## Next phase

Implement fresh prospective confirmation as a separately committed audit-only phase.

Required contract:

- cutoff: strictly after `2026-06-23 18:15:00` MT5 server close
- authoritative current candle files:
  - `goldsharp_m1.csv`
  - `goldsharp_m15.csv`
  - `goldsharp_h1.csv`
  - `goldsharp_h4.csv`
  - `goldsharp_d1.csv`
- latest valid rows are closed by contract
- no future exit information in candidate generation
- candidate rules and IDs remain frozen
- no retuning from prospective results
- unresolved candidates must remain explicit rather than being silently dropped
- no automatic promotion, registration, final signal, MT5 order, Discord, AI API or live hook

## Current user action

None. Do not ask the user to rerun cost stress.

A new root-BAT action may be requested only after the fresh prospective phase implementation is committed and `next_local_action.json` is updated to point to its dedicated phase BAT.

# Current GML1 Handoff

Use these current files first:

- `docs/gold_ml_v1/META_CORE_V1_CURRENT_20260627.md`
- `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_time_causality_audit_20260627.json`
- `config/gold_ml_v1/gml1_target_gate_research_audit_v1_20260627.json`

## Time contract

Every raw CSV `time` value is bar-open time.

- M15 decision time is bar-open plus 15 minutes.
- Entry requires an exact M1 open at decision time.
- H1, H4 and D1 use only the latest bar whose nominal close is no later than decision time.
- Previous-bar conditions require exact 15-minute spacing and reset across gaps.

The full time-causality audit passed.

## Hard research target

A candidate system is unacceptable unless one-position results have:

- at least 250 annualized trades; and
- either Strong-cost win rate at least 60% or Strong PF at least 2.00.

Do not lower this gate and do not treat a validation-only pass as an edge.

## Current audit result

No model or candidate pool has passed the hard target in the following untouched period.

Several validation constructions passed and then failed:

- diverse composite regimes: validation annual 256, WR 61.2%, PF 2.06; following test annual 324, WR 36.4%, PF 0.78;
- adaptive rule portfolio: validation annual 250, WR 61.1%, PF 2.00; following test annual 204, WR 44.2%, PF 1.08;
- candidate-internal loss veto: validation annual 270, WR 59.6%, PF 1.97; following test annual 307, WR 42.0%, PF 0.98;
- exact exit-contract selection: validation annual 349, WR 64.8%; following test annual 413, WR 49.0%, PF 0.88.

A rolling composite loss filter produced 145 trades in 2026 H1, annualized 312, WR 36.6%, PF 0.81.

The existing M1 label contract was exactly reproduced before exit variants were tested. Forty-five additional label contracts, a nonlinear loss veto and an MFE/MAE path model also failed the gate.

## Composite loss findings

Repeated loss-tree features included H4 ADX, H1 spread/ATR, D1 return and volume, H1/H4 Bollinger width, H4 body and slope, and M15 Bollinger/volume interactions. These interactions improved their development period but changed sign or threshold in the following half-year. Absolute-price splits are rejected as nonstationary.

## Current decision

- no promoted model;
- no shadow or live output;
- no Discord or MT5 output;
- validation-only target passes are not retained as deployable candidates;
- the annual 250 and WR60/PF2 target remains fixed.

## Next research stage

Replace fixed direction-entry labels with structural setup-lifecycle labels: setup, trigger, invalidation and post-trigger excursion. Mine multiple independent families and require each family to pass rolling out-of-sample before aggregation. Accept a loss interaction only when its direction repeats across multiple non-overlapping periods.

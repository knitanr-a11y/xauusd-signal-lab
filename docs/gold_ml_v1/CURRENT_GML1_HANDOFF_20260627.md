# Current GML1 Handoff

Current sources:

- `docs/gold_ml_v1/META_CORE_V1_CURRENT_20260627.md`
- `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_time_causality_audit_20260627.json`
- `config/gold_ml_v1/gml1_target_gate_research_audit_v1_20260627.json`
- `config/gold_ml_v1/gml1_lifecycle_rr_research_v1_result_audit_20260627.json`

## Baseline definition

The protected baseline is the original frozen candidate events evaluated without any machine-learning filter.

- preserve all original raw candidate events;
- apply the frozen deduplication and one-position rules;
- use the frozen exact-M1 label and Strong/Extreme cost contracts;
- do not apply Meta Core scores, ML thresholds, calibration or coverage selection.

Meta Core output is a challenger, not the baseline. A new candidate-plus-ML system must be compared against the no-ML baseline first. It is not an improvement when PF rises slightly but total Strong R or trade count falls materially.

Before the next challenger comparison, replay this no-ML baseline from the frozen proposal and label registries and freeze its exact count, WR, PF, Strong R, Extreme R and drawdown in a dedicated baseline audit file.

## Time contract

CSV `time` is bar-open time. M15 decision time is open plus 15 minutes. Entry requires an exact M1 open. H1, H4 and D1 use closed bars only. The time-causality audit passed.

## Hard target

One-position results require at least 250 annualized trades and either Strong win rate at least 60% or Strong PF at least 2.00. Do not lower this gate.

## Lifecycle and RR result

Research labels covered 2 to 24 hours and nominal RR 2 to 4. The existing six-hour TP1.5/SL1.0 contract was exactly reproduced first.

A total of 380 setup-to-trigger variants were generated across trend pullback, compression, breakout preparation, exhaustion, failed breakout and mean reentry. Sixty raw variant-plus-RR streams were positive in at least five of six half-years, all on the LONG side. Their overlap removed the apparent advantage after same-time competition and one-position handling.

Shared-RR validation selection used 8 hours, TP5 ATR and SL1.25 ATR. Validation annualized 314, WR 38.0%, PF 1.59; following test annualized 327, WR 25.0%, PF 0.71.

A family-specific RR portfolio produced validation annualized 727, WR 28.7%, PF 1.33; following test annualized 533, WR 24.6%, PF 0.96.

Partial exit research used half at +1 ATR, then a breakeven or +0.25 ATR runner stop and a +3 to +5 ATR final target. The selected version produced validation annualized 1,141, WR 57.6%, PF 1.11; following test annualized 1,154, WR 52.5%, PF 0.77.

Higher RR and partial exits did not pass the hard gate.

## Current controls

No model is promoted. Shadow, live, Discord and MT5 outputs remain off.

## Next stage

First freeze the exact no-ML baseline audit. Then evaluate candidate-plus-ML challengers only by incremental value over that baseline. Use an explicit state instance for each family: setup onset, invalidation, first valid trigger, reset and cooldown. Learn trigger quality and post-trigger excursion separately per family. Each family must pass rolling out-of-sample before aggregation. Do not tune the failed broad lifecycle pool further on the inspected snapshot.

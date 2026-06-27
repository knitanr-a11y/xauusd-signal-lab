# Current GML1 Handoff

Use only the following files for the current machine-learning and event research structure:

- `docs/gold_ml_v1/META_CORE_V1_CURRENT_20260627.md`
- `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
- `docs/gold_ml_v1/ACTIVE_EVENT_CORE_V1_20260627.md`
- `config/gold_ml_v1/gml1_active_event_core_contract_v1_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_time_causality_audit_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_result_audit_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v3_paired_result_audit_20260627.json`
- `config/gold_ml_v1/gml1_nested_proposer_research_v1_result_audit_20260627.json`

## Time contract

Every raw CSV `time` value is bar-open time.

- M15 decision time is bar-open plus 15 minutes.
- Entry requires an exact M1 open at decision time.
- H1, H4 and D1 use only the latest bar whose nominal close is no later than decision time.
- Previous-bar conditions require exact 15-minute spacing and reset across gaps.

The full time-causality audit passed. No unfinished M15 or higher-timeframe bar entered the feature or event registries.

## Failed fixed event pools

Event Discovery v2 and paired-direction v3 are immutable failed references. Broad manually specified event pools did not give Meta Core stable ranking power. Do not modify or revive them.

## Nested proposer research

Nested shallow-tree rules, a classification proposer and a robust SHORT XGBoost proposer failed outer-test evaluation.

A nested LONG ExtraTrees regression proposer using all causal features except the four cyclical time features produced the first promising result:

- single-seed one-position: 41 trades, Strong `+9.0548R`, PF `1.4759`, Extreme `+6.8495R`;
- F1: 24 trades, Strong `+1.5284R`;
- F3: 17 trades, Strong `+7.5264R`, PF `2.2254`;
- F2 and F4: no accepted trades.

Seed stability:

- F1 was positive in three of five seeds and remains unstable;
- F3 was positive in all five seeds, median Strong `+30.0561R`, median PF `1.8250` on raw proposer events.

A four-of-five seed consensus produced:

- F1 one-position: 16 trades, Strong `+3.8089R`, PF `1.5081`, Extreme `+2.7397R`;
- F3 one-position: 13 trades, Strong `+4.1801R`, PF `1.8153`, Extreme `+3.8536R`.

Meta Core rejected all F1 candidates and added no ranking value in F3 because its calibration slope was zero. The current evidence therefore belongs to the proposer, not to the fixed Meta Core.

## Current decision

The nested five-seed LONG consensus proposer is a research challenger only.

- no promoted model;
- no shadow or live output;
- no SHORT edge established;
- sample count remains below the frozen promotion gate;
- the historical test periods have now been inspected, so further modifications on the same snapshot are performance-informed and cannot certify deployment.

## Next research stage

Freeze the five-seed LONG consensus challenger without changing thresholds. Perform feature-ablation, regime and monthly stability audits. Continue searching for an independent SHORT proposer under a separately versioned contract. Keep Meta Core unchanged until it demonstrates non-zero, stable incremental ranking value.

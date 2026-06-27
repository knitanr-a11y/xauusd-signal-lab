# Current GML1 Handoff

Use only the following files for the current machine-learning and event research structure:

- `docs/gold_ml_v1/META_CORE_V1_CURRENT_20260627.md`
- `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
- `docs/gold_ml_v1/ACTIVE_EVENT_CORE_V1_20260627.md`
- `config/gold_ml_v1/gml1_active_event_core_contract_v1_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_contract_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_time_causality_audit_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v2_result_audit_20260627.json`
- `config/gold_ml_v1/gml1_event_discovery_v3_paired_result_audit_20260627.json`

## Time contract

Every raw CSV `time` value is bar-open time.

- M15 decision time is bar-open plus 15 minutes.
- Entry requires an exact M1 open at decision time.
- H1, H4 and D1 use only the latest bar whose nominal close is no later than decision time.
- Previous-bar conditions require exact 15-minute spacing and reset across gaps.

The full time-causality audit passed. No unfinished M15 or higher-timeframe bar entered the feature or event registries.

## Discovery results

Event Discovery v2 froze fourteen direction-specific events before label join, but the unchanged Meta Core produced conservative Strong `-24.05R`, PF `0.720`. It is an immutable failed reference.

Event Discovery v3 emitted paired LONG and SHORT hypotheses from direction-neutral event gates. It also failed: 82 selected trades, all LONG, Strong `-20.83R`, PF `0.639`. F1 through F3 produced no positive-score selections.

These results show that fixed broad event pools do not give Meta Core stable ranking power. Do not modify v2 or v3 after their results.

## Next research stage

Build a nested walk-forward candidate grammar search:

- generate candidate variants mechanically;
- select candidates using only each fold's train and validation history;
- keep that fold's test period untouched;
- then fit and evaluate Meta Core without changing its architecture;
- report candidate selection stability, direction balance and fold results.

Active Event Core v1 remains the current comparison challenger. No model is promoted and no live output path is enabled.

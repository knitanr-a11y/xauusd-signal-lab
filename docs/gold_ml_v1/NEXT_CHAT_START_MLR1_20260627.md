# GML1-MLR1 — NEXT CHAT START

Read in this order:

1. `config/gold_ml_v1/mlr1_stage_status_20260627.json`
2. `config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json`
3. `config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json`
4. `config/gold_ml_v1/mlr1_stage_ml01_raw_data_audit_20260627.json`
5. `config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json`
6. `config/gold_ml_v1/mlr1_stage_ml02_feature_validation_20260627.json`
7. `config/gold_ml_v1/mlr1_label_contract_v1_20260627.json`
8. `config/gold_ml_v1/mlr1_stage_ml03_label_validation_20260627.json`
9. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML02_CAUSAL_FEATURE_ENGINE_20260627.md`
10. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML03_EXACT_M1_LABEL_ENGINE_20260627.md`
11. existing GOLD_ML_V1 start/handoff documents only as needed for immutable boundaries

Current state:

- ML-00 design contract complete
- ML-01 raw-data and timestamp audit complete
- ML-02 common causal feature engine implemented and container-validated
- ML-03 exact-M1 label engine implemented and container-validated
- ML-02 expected feature rows: 74,168
- ML-02 expected feature registry SHA256: `81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b`
- ML-03 expected resolved label rows: 148,317
- ML-03 expected label registry SHA256: `c897a00905ca3edc47eff29a159beff21e1c1aafc66c6c41558ba3dfd2a0d7ed`
- user-PC Python 3.12 pinned replay remains pending
- next development stage: ML-04 deterministic and linear baselines
- no trained model yet
- existing candidate stack unchanged
- audit-only
- live / final signal / MT5 order / Discord OFF

Do not reuse old Stage2 weights, scalers, thresholds or feature contracts.

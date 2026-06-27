# GML1-MLR1 — NEXT CHAT START

Read in this order:

1. `config/gold_ml_v1/mlr1_stage_status_20260627.json`
2. `config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json`
3. `config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json`
4. `config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json`
5. `config/gold_ml_v1/mlr1_user_pc_pinned_replay_acceptance_20260627.json`
6. `config/gold_ml_v1/mlr1_stage_ml01_raw_data_audit_20260627.json`
7. `config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json`
8. `config/gold_ml_v1/mlr1_stage_ml02_feature_validation_20260627.json`
9. `config/gold_ml_v1/mlr1_label_contract_v1_20260627.json`
10. `config/gold_ml_v1/mlr1_stage_ml03_label_validation_20260627.json`
11. `config/gold_ml_v1/mlr1_ml04_contract_v1_20260627.json`
12. `config/gold_ml_v1/mlr1_stage_ml04_baseline_validation_20260627.json`
13. `config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json`
14. `docs/gold_ml_v1/GML1_MLR1_DATA_SOURCE_ROLE_CONTRACT_20260627.md`
15. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML02_CAUSAL_FEATURE_ENGINE_20260627.md`
16. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML03_EXACT_M1_LABEL_ENGINE_20260627.md`
17. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML04_BASELINES_20260627.md`
18. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML04_RESULT_AUDIT_20260627.md`
19. existing GOLD_ML_V1 start/handoff documents only as needed for immutable boundaries

Current state:

- ML-00 design contract complete
- ML-01 raw-data and timestamp audit complete
- ML-02 common causal feature engine implemented, validated and accepted on Windows Python 3.12
- ML-03 exact-M1 label engine implemented, validated and accepted on Windows Python 3.12
- ML-04 deterministic and linear baseline replay complete and audited
- all uploaded ML-04 artifact hashes verified
- LONG linear lanes rejected
- Ridge lanes rejected
- SHORT multinomial logistic shows research ranking value but is not shadow-ready
- no ML-04 policy passed the frozen shadow gate
- next stage: ML-05 histogram gradient boosting
- ML-05 must include full 161-feature and no-server-hour ablation lanes
- historical development source: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\gold_v3_2023_2026`
- live operational source: Files-root `goldsharp_*.csv`
- historical and live sources must never fallback to, replace or silently concatenate with each other
- accepted ML-02 feature rows: 74,168
- accepted ML-02 feature registry SHA256: `81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b`
- accepted ML-03 resolved label rows: 148,317
- accepted ML-03 label registry SHA256: `c897a00905ca3edc47eff29a159beff21e1c1aafc66c6c41558ba3dfd2a0d7ed`
- goldsharp live adapter is not implemented yet
- no model is promoted
- existing candidate stack unchanged
- audit-only
- live / final signal / MT5 order / Discord OFF

Do not reuse old Stage2 weights, scalers, thresholds or feature contracts.

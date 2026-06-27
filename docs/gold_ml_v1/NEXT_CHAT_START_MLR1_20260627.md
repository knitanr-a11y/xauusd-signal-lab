# GML1-MLR1 — NEXT CHAT START

Read in this order:

1. `config/gold_ml_v1/mlr1_stage_status_20260627.json`
2. `config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`
3. `config/gold_ml_v1/mlr1_ml_native_candidate_contract_v1_20260627.json`
4. `config/gold_ml_v1/mlr1_stage_ml05a_candidate_proposal_validation_20260627.json`
5. `config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json`
6. `config/gold_ml_v1/mlr1_user_pc_pinned_replay_acceptance_20260627.json`
7. `config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json`
8. `config/gold_ml_v1/mlr1_label_contract_v1_20260627.json`
9. `config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json`
10. `docs/gold_ml_v1/GML1_MLR1_STAGE_ML04_RESULT_AUDIT_20260627.md`
11. existing GOLD_ML_V1 start/handoff documents only as needed for immutable boundaries

Current state:

- ML-00 through ML-04 complete and audited
- no ML-04 model promoted
- current stage: ML-05A
- sixteen nonreproducible current-stack candidates are excluded from every MLR1 model input and fallback
- nine exact-replay legacy candidates are benchmark-only because they are all LONG and belong to two nested historically tuned lineages
- primary pool is twelve new ML-native candidates across six symmetric LONG/SHORT structural families
- candidate definitions are frozen before label or performance review
- label-free proposal generator is implemented
- next step: run unit tests and `scripts\gold_ml_v1\mlr1\run_build_ml_native_candidate_proposals.bat`
- review proposal counts, year coverage, direction balance and overlap only
- do not join ML-03 labels until every candidate passes the density gate or a new contract version is created
- density gate: 100 to 5000 proposals and at least three calendar years per candidate
- historical development source remains `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\gold_v3_2023_2026`
- live operational source remains Files-root `goldsharp_*.csv`
- historical and live sources must never fallback to, replace or silently concatenate with each other
- no labels joined to candidates
- no candidate performance reviewed
- no model trained or promoted
- existing historical candidate stack unchanged
- audit-only
- live / final signal / MT5 order / Discord OFF

Do not reuse old Stage2 weights, scalers, thresholds or feature contracts.

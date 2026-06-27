# GML1-MLR1 — NEXT CHAT START

Read first:

1. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_MLR1_ML05A_DENSITY_AUDITED_20260627.md`
2. `config/gold_ml_v1/mlr1_stage_status_addendum_ml05a_density_20260627.json`
3. `config/gold_ml_v1/mlr1_stage_ml05a_density_audit_v1_20260627.json`
4. `config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`
5. `config/gold_ml_v1/mlr1_ml_native_candidate_contract_v1_20260627.json`
6. `scripts/gold_ml_v1/mlr1/build_ml_native_candidate_proposals.py`
7. `config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json`
8. `config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json`
9. `config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json`
10. `config/gold_ml_v1/mlr1_user_pc_pinned_replay_acceptance_20260627.json`
11. `config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json`

Current state:

- ML-00 through ML-04 are complete and audited.
- The final architecture is specialist candidate proposals followed by machine-learning selection.
- Sixteen nonreproducible existing candidates are excluded from MLR1 model use.
- Nine exact-replay legacy candidates are benchmark-only.
- Twelve ML-native v1 candidates were generated without label or performance review.
- Proposal registry: 3,180 rows, 166 columns, SHA256 `d47a745402f4be01d7be5e1a6e830f33515e7317768363d745cff8ea09fb8219`.
- Accepted v1 families: MLC-001, MLC-003, MLC-006.
- Density-only v2 required: MLC-002, MLC-004, MLC-005.
- Do not join ML-03 labels yet.
- Do not inspect candidate PF, win rate or R while revising density.
- Next task: build label-free condition funnels for failed families, freeze v2, then rebuild the combined primary proposal pool.
- Historical source is the fixed `gold_v3_2023_2026` directory.
- Future live source is Files-root `goldsharp_*.csv` only.
- Existing historical candidate stack remains unchanged.
- Audit-only; no model promotion or live activation.

Final objective:

Use deterministic specialist candidates plus a calibrated candidate meta-model and deterministic risk arbitration, validate prospectively on live closed-bar data, and only after separate gates and authorization proceed to automated XAUUSD execution.

Do not reuse old Stage2 weights, scalers, thresholds or feature contracts.

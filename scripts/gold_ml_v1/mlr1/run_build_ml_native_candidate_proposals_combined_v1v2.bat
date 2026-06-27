@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3.12 scripts\gold_ml_v1\mlr1\build_ml_native_candidate_proposals_combined_v1v2.py --feature-registry outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz --feature-contract config\gold_ml_v1\mlr1_feature_contract_v1_20260627.json --v1-candidate-contract config\gold_ml_v1\mlr1_ml_native_candidate_contract_v1_20260627.json --v2-candidate-contract config\gold_ml_v1\mlr1_ml_native_candidate_contract_v2_density_20260627.json --v1-density-audit config\gold_ml_v1\mlr1_stage_ml05a_density_audit_v1_20260627.json --output-dir outputs\gml1\ml05a_v2
exit /b %ERRORLEVEL%

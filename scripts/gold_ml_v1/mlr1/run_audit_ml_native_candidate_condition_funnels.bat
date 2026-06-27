@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3.12 scripts\gold_ml_v1\mlr1\audit_ml_native_candidate_condition_funnels.py --feature-registry outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz --feature-contract config\gold_ml_v1\mlr1_feature_contract_v1_20260627.json --candidate-contract config\gold_ml_v1\mlr1_ml_native_candidate_contract_v1_20260627.json --density-audit config\gold_ml_v1\mlr1_stage_ml05a_density_audit_v1_20260627.json --output-dir outputs\gold_ml_v1\mlr1\ml05a_condition_funnel_v1
exit /b %ERRORLEVEL%

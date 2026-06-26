@echo off
setlocal
cd /d "%~dp0\..\..\.."
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
py -3.12 scripts\gold_ml_v1\mlr1\run_ml04_baselines.py --feature-registry outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz --label-registry outputs\gold_ml_v1\mlr1\ml03_labels_v1\mlr1_labels_v1.csv.gz --feature-contract config\gold_ml_v1\mlr1_feature_contract_v1_20260627.json --ml04-contract config\gold_ml_v1\mlr1_ml04_contract_v1_20260627.json --output-dir outputs\gold_ml_v1\mlr1\ml04_baselines_v1
exit /b %ERRORLEVEL%

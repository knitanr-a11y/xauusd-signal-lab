@echo off
setlocal
cd /d "%~dp0\..\..\.."
set FEATURES=outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz
set COLUMNS=outputs\gml1\ml05b\mlr1_candidate_event_columns_v1.json
set OUTPUT=outputs\gml1\mlr2_candidates_v1
if not exist "%FEATURES%" exit /b 2
if not exist "%COLUMNS%" exit /b 2
py -3.12 scripts\gold_ml_v1\mlr1\build_mlr2_candidate_proposals_v1.py --feature-registry "%FEATURES%" --feature-columns "%COLUMNS%" --output-dir "%OUTPUT%"
exit /b %ERRORLEVEL%

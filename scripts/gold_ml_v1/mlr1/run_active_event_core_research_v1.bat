@echo off
setlocal
cd /d "%~dp0\..\..\.."

set FEATURES=outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz
set LABELS=outputs\gold_ml_v1\mlr1\ml03_labels_v1\mlr1_labels_v1.csv.gz
set COLUMNS=outputs\gml1\ml05b\mlr1_candidate_event_columns_v1.json
set ROOT=outputs\gml1\active_event_core_v1

if not exist "%FEATURES%" exit /b 2
if not exist "%LABELS%" exit /b 2
if not exist "%COLUMNS%" exit /b 2

py -3.12 scripts\gold_ml_v1\mlr1\build_active_event_core_proposals_v1.py --feature-registry "%FEATURES%" --feature-columns "%COLUMNS%" --output-dir "%ROOT%\proposals"
if errorlevel 1 exit /b %ERRORLEVEL%

py -3.12 scripts\gold_ml_v1\mlr1\build_active_event_registry_v1.py --proposals "%ROOT%\proposals\gml1_active_event_core_proposals_v1.csv.gz" --labels "%LABELS%" --join-contract config\gold_ml_v1\gml1_active_event_join_contract_v1_20260627.json --output-dir "%ROOT%\events"
if errorlevel 1 exit /b %ERRORLEVEL%

py -3.12 scripts\gold_ml_v1\mlr1\run_mlr1_meta_model_research.py --event-registry "%ROOT%\events\gml1_active_event_registry_v1.csv.gz" --feature-registry "%FEATURES%" --columns-contract "%COLUMNS%" --core-contract config\gold_ml_v1\mlr1_meta_model_core_contract_v1_20260627.json --output-dir "%ROOT%\meta_research"
exit /b %ERRORLEVEL%

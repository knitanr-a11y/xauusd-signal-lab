@echo off
setlocal
cd /d "%~dp0\..\..\.."

set EVENT=outputs\gml1\ml05b\mlr1_candidate_event_registry_v1.csv.gz
set FEATURES=outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz
set COLUMNS=outputs\gml1\ml05b\mlr1_candidate_event_columns_v1.json
set CONTRACT=config\gold_ml_v1\mlr1_meta_model_core_contract_v1_20260627.json
set OUTPUT=outputs\gml1\meta_core_research_v1

if not exist "%EVENT%" echo Missing %EVENT% & exit /b 2
if not exist "%FEATURES%" echo Missing %FEATURES% & exit /b 2
if not exist "%COLUMNS%" echo Missing %COLUMNS% & exit /b 2

py -3.12 scripts\gold_ml_v1\mlr1\run_mlr1_meta_model_research.py ^
  --event-registry "%EVENT%" ^
  --feature-registry "%FEATURES%" ^
  --columns-contract "%COLUMNS%" ^
  --core-contract "%CONTRACT%" ^
  --output-dir "%OUTPUT%" ^
  --enforce-reference-sha
if errorlevel 1 exit /b %ERRORLEVEL%

py -3.12 scripts\gold_ml_v1\mlr1\verify_mlr1_meta_core_reference.py ^
  --summary "%OUTPUT%\mlr1_meta_core_summary_v1.json"
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0\..\..\.."

if "%~1"=="" (
  echo Usage: run_build_labels.bat "C:\path\to\raw"
  exit /b 1
)

py -3.12 -m pip install -r scripts\gold_ml_v1\mlr1\requirements-mlr1.txt
if errorlevel 1 exit /b 4

py -3.12 scripts\gold_ml_v1\mlr1\build_labels.py ^
  --raw-dir "%~1" ^
  --feature-registry outputs\gold_ml_v1\mlr1\ml02_features_v1\mlr1_features_v1.csv.gz ^
  --contract config\gold_ml_v1\mlr1_label_contract_v1_20260627.json ^
  --output-dir outputs\gold_ml_v1\mlr1\ml03_labels_v1

set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
pause
exit /b %RC%

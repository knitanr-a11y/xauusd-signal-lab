@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\..\.."
set "RUNTIME=%CD%\scripts\gold_v3_runtime"
set "FILES_DIR="
if defined GOLD_V3_MQL5_FILES set "FILES_DIR=%GOLD_V3_MQL5_FILES%"
if not defined FILES_DIR (
  for /d %%D in ("%APPDATA%\MetaQuotes\Terminal\*") do (
    if not defined FILES_DIR (
      set "CANDIDATE=%%~fD\MQL5\Files"
      if exist "!CANDIDATE!\goldsharp_m1.csv" if exist "!CANDIDATE!\goldsharp_m5.csv" if exist "!CANDIDATE!\goldsharp_m15.csv" if exist "!CANDIDATE!\goldsharp_h1.csv" if exist "!CANDIDATE!\goldsharp_h4.csv" if exist "!CANDIDATE!\goldsharp_d1.csv" if exist "!CANDIDATE!\us500cashsharp_m15.csv" if exist "!CANDIDATE!\us100cashsharp_m15.csv" set "FILES_DIR=!CANDIDATE!"
    )
  )
)
if not defined FILES_DIR (echo [BLOCKED] MT5 Files folder was not found.& pause& exit /b 2)
where python >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=python") else (set "PYTHON_CMD=py -3")
%PYTHON_CMD% -c "import numpy, pandas, lightgbm" >nul 2>&1
if errorlevel 1 %PYTHON_CMD% -m pip install numpy pandas lightgbm
set "MODEL_DIR=%RUNTIME%\models\gold_v3_289"
if not exist "%MODEL_DIR%\stage280_rev_long_2026_model.txt" (
  %PYTHON_CMD% "%RUNTIME%\gold_v3_289_train_live_models_audit.py" --candle-dir "%FILES_DIR%"
  if errorlevel 1 (echo [BLOCKED] Model training parity failed.& pause& exit /b 3)
)
set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\292_safe_portfolio_live"
echo Stage292 continuous live monitor
echo MT5 Files: %FILES_DIR%
echo Stop: Ctrl+C
:LOOP
%PYTHON_CMD% "%RUNTIME%\gold_v3_69_live_csv_condition_detector_audit.py" --candle-dir "%FILES_DIR%" >nul 2>&1
if not errorlevel 1 %PYTHON_CMD% "%RUNTIME%\gold_v3_292_safe_portfolio_live.py" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%"
if exist "%OUT_DIR%\gold_v3_292_summary.json" (
  cls
  echo Stage292 safe portfolio live - %date% %time%
  echo MT5 Files: %FILES_DIR%
  echo.
  type "%OUT_DIR%\gold_v3_292_summary.json"
  echo.
  echo Stop: Ctrl+C
)
timeout /t 60 /nobreak >nul
goto LOOP

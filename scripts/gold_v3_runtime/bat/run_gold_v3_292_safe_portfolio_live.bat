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
if not defined FILES_DIR (
  echo [BLOCKED] MT5 Files folder was not found.
  pause
  exit /b 2
)
where python >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=python") else (set "PYTHON_CMD=py -3")
%PYTHON_CMD% -c "import numpy, pandas, lightgbm" >nul 2>&1
if errorlevel 1 (
  %PYTHON_CMD% -m pip install numpy pandas lightgbm
  if errorlevel 1 (echo [BLOCKED] Python package installation failed.& pause& exit /b 3)
)
set "MODEL_DIR=%RUNTIME%\models\gold_v3_289"
set "TRAIN_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\289_training_history"
if not exist "%TRAIN_DIR%" mkdir "%TRAIN_DIR%"
for %%F in (h1 h4 d1) do copy /Y "%FILES_DIR%\goldsharp_%%F.csv" "%TRAIN_DIR%\goldsharp_%%F.csv" >nul
if not exist "%MODEL_DIR%\stage280_rev_long_2026_model.txt" (
  if not exist "%TRAIN_DIR%\goldsharp_m1.csv" (
    echo [BLOCKED] Historical GOLD M1 training file is missing.
    echo Run install_gold_v3_289_training_m1_exporter.bat, compile the script in MetaEditor,
    echo and run ExportGoldStage289TrainingM1 once on a GOLD chart.
    pause
    exit /b 4
  )
  echo [INFO] Checking Stage289 training-history coverage...
  %PYTHON_CMD% "%RUNTIME%\gold_v3_289_training_history_preflight.py" --candle-dir "%TRAIN_DIR%"
  if errorlevel 1 (
    echo [BLOCKED] Training history is incomplete.
    echo Rerun the updated ExportGoldStage289TrainingM1 script to refresh M1, M5 and M15.
    pause
    exit /b 5
  )
  echo [INFO] Training Stage280/281 once from the audited historical staging folder.
  %PYTHON_CMD% "%RUNTIME%\gold_v3_289_train_live_models_audit.py" --candle-dir "%TRAIN_DIR%"
  if errorlevel 1 (echo [BLOCKED] Model training parity failed.& pause& exit /b 6)
)
echo [1/2] Refreshing BASE conditions...
%PYTHON_CMD% "%RUNTIME%\gold_v3_69_live_csv_condition_detector_audit.py" --candle-dir "%FILES_DIR%"
if errorlevel 1 (echo [BLOCKED] Stage69 failed.& pause& exit /b 7)
echo [2/2] Running resolved-only safe portfolio controller...
set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\292_safe_portfolio_live"
%PYTHON_CMD% "%RUNTIME%\gold_v3_292_safe_portfolio_live.py" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%"
set "RC=%ERRORLEVEL%"
echo.
if exist "%OUT_DIR%\gold_v3_292_summary.json" type "%OUT_DIR%\gold_v3_292_summary.json"
echo.
echo Output folder: %OUT_DIR%
pause
exit /b %RC%

@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GOLD V3 Stage289 Live Candle ML Safe Shadow
set "REPO_ROOT=%~dp0..\..\.."
set "RUNTIME_DIR=%REPO_ROOT%\scripts\gold_v3_runtime"
set "TRAINER=%RUNTIME_DIR%\gold_v3_289_train_live_models_audit.py"
set "VALIDATOR=%RUNTIME_DIR%\gold_v3_289_artifacts.py"
set "RUNNER=%RUNTIME_DIR%\gold_v3_289_live_candle_ml_safe_shadow_audit.py"
set "MODEL_DIR=%RUNTIME_DIR%\models\gold_v3_289"
if defined GOLD_V3_MQL5_FILES (
  set "FILES_DIR=%GOLD_V3_MQL5_FILES%"
) else (
  set "FILES_DIR=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
)
set "OUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\289c"
where py >nul 2>nul
if errorlevel 1 (echo [BLOCKED] py.exe not found.& pause& exit /b 1)
py -c "import pandas,numpy,lightgbm" >nul 2>nul
if errorlevel 1 (echo [BLOCKED] pandas numpy lightgbm are required.& pause& exit /b 1)
for %%F in (goldsharp_m1.csv goldsharp_m5.csv goldsharp_m15.csv goldsharp_h1.csv goldsharp_h4.csv goldsharp_d1.csv) do (
  if not exist "%FILES_DIR%\%%F" (echo [BLOCKED] Missing %%F& pause& exit /b 1)
)
if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
rem Never trust model files by existence alone.
py "%VALIDATOR%" --model-dir "%MODEL_DIR%" >nul 2>nul
if errorlevel 1 goto TRAIN_MODELS
goto RUN_SHADOW
:TRAIN_MODELS
echo Training exact Stage280 and Stage281 models from closed live candle history...
py "%TRAINER%" --candle-dir "%FILES_DIR%" --output-dir "%MODEL_DIR%" --force
if errorlevel 1 (echo [BLOCKED] Model training or exact parity failed.& pause& exit /b 1)
py "%VALIDATOR%" --model-dir "%MODEL_DIR%"
if errorlevel 1 (echo [BLOCKED] New model bundle failed SHA or contract validation.& pause& exit /b 1)
:RUN_SHADOW
if defined GOLD_V3_BASE_RESOLVED_CSV (
  py "%RUNNER%" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%" --base-resolved-csv "%GOLD_V3_BASE_RESOLVED_CSV%"
) else if exist "%OUT_DIR%\gold_v3_289_base_resolved_import.csv" (
  py "%RUNNER%" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%" --base-resolved-csv "%OUT_DIR%\gold_v3_289_base_resolved_import.csv"
) else (
  py "%RUNNER%" --candle-dir "%FILES_DIR%" --output-dir "%OUT_DIR%"
)
set "RC=%ERRORLEVEL%"
echo.
echo Output: %OUT_DIR%\paste_me.txt
if exist "%OUT_DIR%\paste_me.txt" type "%OUT_DIR%\paste_me.txt"
pause
exit /b %RC%

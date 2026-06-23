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
      if exist "!CANDIDATE!\FX_OUTPUTS\gold_v3\289_training_history\goldsharp_m1.csv" set "FILES_DIR=!CANDIDATE!"
    )
  )
)
if not defined FILES_DIR (
  echo [BLOCKED] Stage289 training-history folder was not found.
  pause
  exit /b 2
)
where python >nul 2>&1
if not errorlevel 1 (set "PYTHON_CMD=python") else (set "PYTHON_CMD=py -3")
set "TRAIN_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\289_training_history"
set "READINESS_JSON=%TRAIN_DIR%\stage303_stage280_block_stage281_readiness.json"
echo [INFO] Running Stage280-block / Stage281-readiness diagnostic...
%PYTHON_CMD% "%RUNTIME%\gold_v3_303_stage280_block_stage281_readiness.py" --repo-root "%CD%" --output "%READINESS_JSON%"
set "RC=%ERRORLEVEL%"
echo.
echo Readiness file:
echo %READINESS_JSON%
echo.
pause
exit /b %RC%

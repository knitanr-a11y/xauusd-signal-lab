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
where git >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)
if errorlevel 1 (
  for /d %%G in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do (
    if exist "%%~fG\resources\app\git\cmd\git.exe" set "PATH=%%~fG\resources\app\git\cmd;%PATH%"
  )
)
where git >nul 2>&1
if errorlevel 1 (
  echo [BLOCKED] Git executable was not found. Open GitHub Desktop once, then run this BAT again.
  pause
  exit /b 3
)
set "TRAIN_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v3\289_training_history"
set "RECOVERY_JSON=%TRAIN_DIR%\stage301_stage280_artifact_recovery.json"
echo [INFO] Running Stage280 artifact recovery diagnostic...
%PYTHON_CMD% "%RUNTIME%\gold_v3_301_stage280_artifact_recovery_runner.py" --repo-root "%CD%" --scan-root "%FILES_DIR%" --output "%RECOVERY_JSON%"
set "RC=%ERRORLEVEL%"
echo.
echo Recovery file:
echo %RECOVERY_JSON%
echo.
pause
exit /b %RC%

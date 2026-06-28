@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "LOOP_MODE=0"
set "EXTRA_ARGS=%*"
if /I "%~1"=="--loop" (
  set "LOOP_MODE=1"
  set "EXTRA_ARGS="
)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "PYTHON_SCRIPT=%SCRIPT_DIR%run_live_connected_once.py"
set "OUTPUT_DIR=%REPO_ROOT%\outputs\gold_ml_v1\live_research_challenger"
set "RUN_LOG=%OUTPUT_DIR%\run_live_once_last.log"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: could not create output directory.
  echo "%OUTPUT_DIR%"
  if "%LOOP_MODE%"=="0" pause
  exit /b 2
)

if not exist "%PYTHON_SCRIPT%" (
  echo ERROR: connected live one-shot Python script was not found.
  echo "%PYTHON_SCRIPT%"
  if "%LOOP_MODE%"=="0" pause
  exit /b 2
)

>"%RUN_LOG%" echo [%date% %time%] RUN_LIVE_CONNECTED_ONCE_START
py -3.12 "%PYTHON_SCRIPT%" --output-dir "%OUTPUT_DIR%" !EXTRA_ARGS! >>"%RUN_LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

if "%LOOP_MODE%"=="0" (
  echo.
  type "%RUN_LOG%"
  echo.
  if "%EXIT_CODE%"=="0" (
    echo PASS.
  ) else if "%EXIT_CODE%"=="5" (
    echo DEFERRED. The next run may process the bars after MT5 finishes writing them.
  ) else if "%EXIT_CODE%"=="4" (
    echo BUSY. Another one-shot process is running.
  ) else (
    echo FAILED. Exit code: %EXIT_CODE%
  )
  echo Log: "%RUN_LOG%"
  echo.
  pause
)

exit /b %EXIT_CODE%

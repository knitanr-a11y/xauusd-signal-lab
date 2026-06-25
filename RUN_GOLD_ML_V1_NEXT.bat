@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [ERROR] Python 3.12 could not be found.
  echo Install Python 3.12 or run the previously supplied setup BAT once.
  pause
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - ONE CLICK NEXT ACTION

echo ============================================================
%PYTHON_CMD% scripts\gold_ml_v1\run_next_local.py --repo-root "%CD%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [DONE] Current GOLD_ML_V1 action completed successfully.
) else (
  echo [FAIL] Exit code: %RC%
  echo Check outputs\gold_ml_v1\next_action\LATEST_NEXT_ACTION.txt
)

echo.
pause
exit /b %RC%

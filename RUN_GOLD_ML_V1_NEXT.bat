@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GOLD_ML_V1 - ONE CLICK NEXT ACTION

set "PASTE_ME=%CD%\PASTE_ME_GOLD_ML_V1.txt"
set "NEXT_OUTPUT=%CD%\outputs\gold_ml_v1\next_action"
if not exist "%NEXT_OUTPUT%" mkdir "%NEXT_OUTPUT%"

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  >"%PASTE_ME%" echo GOLD_ML_V1 PASTE ME
  >>"%PASTE_ME%" echo Copy everything in this file and paste it into ChatGPT.
  >>"%PASTE_ME%" echo status=FAIL
  >>"%PASTE_ME%" echo exit_code=4
  >>"%PASTE_ME%" echo error=Python 3.12 could not be found.
  >>"%PASTE_ME%" echo repo_root=%CD%
  copy /y "%PASTE_ME%" "%NEXT_OUTPUT%\PASTE_ME_GOLD_ML_V1.txt" >nul 2>nul
  echo [ERROR] Python 3.12 could not be found.
  echo A diagnostic file was created:
  echo %PASTE_ME%
  start "" notepad.exe "%PASTE_ME%" >nul 2>nul
  echo.
  echo Press any key to close this window.
  pause >nul
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - ONE CLICK NEXT ACTION
echo Launcher revision: PASTE_ME_V1_20260625
echo ============================================================
%PYTHON_CMD% scripts\gold_ml_v1\run_next_local.py --repo-root "%CD%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [DONE] Current GOLD_ML_V1 action completed successfully.
) else (
  echo [FAIL] Exit code: %RC%
)

echo.
if exist "%PASTE_ME%" (
  echo The copy-and-paste diagnostic file is here:
  echo %PASTE_ME%
  echo.
  echo It will now open in Notepad.
  start "" notepad.exe "%PASTE_ME%" >nul 2>nul
) else (
  echo [WARNING] PASTE_ME file was not created by Python.
  >"%PASTE_ME%" echo GOLD_ML_V1 PASTE ME
  >>"%PASTE_ME%" echo status=FAIL
  >>"%PASTE_ME%" echo exit_code=%RC%
  >>"%PASTE_ME%" echo error=PASTE_ME was not created by the dispatcher.
  >>"%PASTE_ME%" echo Check outputs\gold_ml_v1\next_action\LATEST_NEXT_ACTION.txt
  start "" notepad.exe "%PASTE_ME%" >nul 2>nul
)

echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%

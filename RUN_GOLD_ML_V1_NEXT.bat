@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GOLD_ML_V1 - ONE CLICK NEXT ACTION

set "PASTE_ME=%CD%\PASTE_ME_GOLD_ML_V1.txt"
set "NEXT_OUTPUT=%CD%\outputs\gold_ml_v1\next_action"
set "OUTPUT_PASTE_ME=%NEXT_OUTPUT%\PASTE_ME_GOLD_ML_V1.txt"
set "BOOTSTRAP_ERROR=%NEXT_OUTPUT%\DISPATCHER_BOOTSTRAP_ERROR.txt"
if not exist "%NEXT_OUTPUT%" mkdir "%NEXT_OUTPUT%"

rem Never show a stale diagnostic from a previous attempt.
if exist "%PASTE_ME%" del /q "%PASTE_ME%" >nul 2>nul
if exist "%OUTPUT_PASTE_ME%" del /q "%OUTPUT_PASTE_ME%" >nul 2>nul
if exist "%BOOTSTRAP_ERROR%" del /q "%BOOTSTRAP_ERROR%" >nul 2>nul

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
  copy /y "%PASTE_ME%" "%OUTPUT_PASTE_ME%" >nul 2>nul
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
echo Launcher revision: PASTE_ME_V2_20260625
echo ============================================================
%PYTHON_CMD% scripts\gold_ml_v1\run_next_local.py --repo-root "%CD%" 2>"%BOOTSTRAP_ERROR%"
set "RC=%ERRORLEVEL%"

if exist "%BOOTSTRAP_ERROR%" (
  for %%A in ("%BOOTSTRAP_ERROR%") do if %%~zA GTR 0 (
    echo.
    echo ===== DISPATCHER STDERR =====
    type "%BOOTSTRAP_ERROR%"
    echo ===== END DISPATCHER STDERR =====
  )
)

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
  >>"%PASTE_ME%" echo Copy everything in this file and paste it into ChatGPT.
  >>"%PASTE_ME%" echo status=FAIL
  >>"%PASTE_ME%" echo exit_code=%RC%
  >>"%PASTE_ME%" echo error=PASTE_ME was not created by the dispatcher.
  >>"%PASTE_ME%" echo repo_root=%CD%
  if exist "%BOOTSTRAP_ERROR%" (
    >>"%PASTE_ME%" echo.
    >>"%PASTE_ME%" echo ===== DISPATCHER BOOTSTRAP ERROR =====
    type "%BOOTSTRAP_ERROR%" >>"%PASTE_ME%"
    >>"%PASTE_ME%" echo ===== END DISPATCHER BOOTSTRAP ERROR =====
  )
  >>"%PASTE_ME%" echo.
  >>"%PASTE_ME%" echo Check outputs\gold_ml_v1\next_action\LATEST_NEXT_ACTION.txt
  copy /y "%PASTE_ME%" "%OUTPUT_PASTE_ME%" >nul 2>nul
  start "" notepad.exe "%PASTE_ME%" >nul 2>nul
)

echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%

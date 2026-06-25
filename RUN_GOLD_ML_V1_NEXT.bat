@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GOLD_ML_V1 - ONE CLICK NEXT ACTION

set "NEXT_OUTPUT=%CD%\outputs\gold_ml_v1\next_action"
set "COST_OUTPUT=%CD%\outputs\gold_ml_v1\cost_stress_raw_reconstructed"
set "UPLOAD_FILE=%COST_OUTPUT%\UPLOAD_THIS_GOLD_ML_V1.txt"
set "BOOTSTRAP_ERROR=%NEXT_OUTPUT%\DISPATCHER_BOOTSTRAP_ERROR.txt"
if not exist "%NEXT_OUTPUT%" mkdir "%NEXT_OUTPUT%"
if not exist "%COST_OUTPUT%" mkdir "%COST_OUTPUT%"

rem Never show a stale diagnostic from a previous attempt.
if exist "%UPLOAD_FILE%" del /q "%UPLOAD_FILE%" >nul 2>nul
if exist "%BOOTSTRAP_ERROR%" del /q "%BOOTSTRAP_ERROR%" >nul 2>nul

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  >"%UPLOAD_FILE%" echo GOLD_ML_V1 UPLOAD FILE
  >>"%UPLOAD_FILE%" echo Upload this file directly to ChatGPT.
  >>"%UPLOAD_FILE%" echo status=FAIL
  >>"%UPLOAD_FILE%" echo exit_code=4
  >>"%UPLOAD_FILE%" echo error=Python 3.12 could not be found.
  >>"%UPLOAD_FILE%" echo repo_root=%CD%
  echo [ERROR] Python 3.12 could not be found.
  echo Upload this file to ChatGPT:
  echo %UPLOAD_FILE%
  start "" explorer.exe /select,"%UPLOAD_FILE%" >nul 2>nul
  echo.
  echo Press any key to close this window.
  pause >nul
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - ONE CLICK NEXT ACTION
echo Launcher revision: UPLOAD_FILE_V1_20260625
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
if exist "%UPLOAD_FILE%" (
  echo Upload this file to ChatGPT:
  echo %UPLOAD_FILE%
  echo.
  echo The output folder will now open with the file selected.
  start "" explorer.exe /select,"%UPLOAD_FILE%" >nul 2>nul
) else (
  echo [WARNING] Upload file was not created by Python.
  >"%UPLOAD_FILE%" echo GOLD_ML_V1 UPLOAD FILE
  >>"%UPLOAD_FILE%" echo Upload this file directly to ChatGPT.
  >>"%UPLOAD_FILE%" echo status=FAIL
  >>"%UPLOAD_FILE%" echo exit_code=%RC%
  >>"%UPLOAD_FILE%" echo error=UPLOAD_THIS_GOLD_ML_V1.txt was not created by the dispatcher.
  >>"%UPLOAD_FILE%" echo repo_root=%CD%
  if exist "%BOOTSTRAP_ERROR%" (
    >>"%UPLOAD_FILE%" echo.
    >>"%UPLOAD_FILE%" echo ===== DISPATCHER BOOTSTRAP ERROR =====
    type "%BOOTSTRAP_ERROR%" >>"%UPLOAD_FILE%"
    >>"%UPLOAD_FILE%" echo ===== END DISPATCHER BOOTSTRAP ERROR =====
  )
  start "" explorer.exe /select,"%UPLOAD_FILE%" >nul 2>nul
)

echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%

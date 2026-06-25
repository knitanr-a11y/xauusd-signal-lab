@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title GOLD_ML_V1 - ONE CLICK NEXT ACTION

set "NEXT_OUTPUT=%CD%\outputs\gold_ml_v1\next_action"
set "UPLOAD_PATH_FILE=%NEXT_OUTPUT%\CURRENT_UPLOAD_PATH.txt"
set "FALLBACK_UPLOAD=%NEXT_OUTPUT%\UPLOAD_THIS_GOLD_ML_V1.txt"
set "BOOTSTRAP_ERROR=%NEXT_OUTPUT%\DISPATCHER_BOOTSTRAP_ERROR.txt"
if not exist "%NEXT_OUTPUT%" mkdir "%NEXT_OUTPUT%"

rem Never reuse an upload path or bootstrap error from a previous attempt.
if exist "%UPLOAD_PATH_FILE%" del /q "%UPLOAD_PATH_FILE%" >nul 2>nul
if exist "%FALLBACK_UPLOAD%" del /q "%FALLBACK_UPLOAD%" >nul 2>nul
if exist "%BOOTSTRAP_ERROR%" del /q "%BOOTSTRAP_ERROR%" >nul 2>nul

set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  >"%FALLBACK_UPLOAD%" echo GOLD_ML_V1 UPLOAD FILE
  >>"%FALLBACK_UPLOAD%" echo Upload this file directly to ChatGPT.
  >>"%FALLBACK_UPLOAD%" echo status=FAIL
  >>"%FALLBACK_UPLOAD%" echo exit_code=4
  >>"%FALLBACK_UPLOAD%" echo error=Python 3.12 could not be found.
  >>"%FALLBACK_UPLOAD%" echo repo_root=%CD%
  >"%UPLOAD_PATH_FILE%" echo %FALLBACK_UPLOAD%
  echo [ERROR] Python 3.12 could not be found.
  echo Upload this file to ChatGPT:
  echo %FALLBACK_UPLOAD%
  start "" explorer.exe /select,"%FALLBACK_UPLOAD%" >nul 2>nul
  echo.
  echo Press any key to close this window.
  pause >nul
  exit /b 4
)

echo ============================================================
echo GOLD_ML_V1 - ONE CLICK NEXT ACTION
echo Launcher revision: PHASE_UPLOAD_V2_20260625
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

set "UPLOAD_FILE="
if exist "%UPLOAD_PATH_FILE%" set /p "UPLOAD_FILE="<"%UPLOAD_PATH_FILE%"
if not defined UPLOAD_FILE set "UPLOAD_FILE=%FALLBACK_UPLOAD%"

if not exist "!UPLOAD_FILE!" (
  echo [WARNING] Phase upload file was not created by Python.
  >"%FALLBACK_UPLOAD%" echo GOLD_ML_V1 UPLOAD FILE
  >>"%FALLBACK_UPLOAD%" echo Upload this file directly to ChatGPT.
  >>"%FALLBACK_UPLOAD%" echo status=FAIL
  >>"%FALLBACK_UPLOAD%" echo exit_code=%RC%
  >>"%FALLBACK_UPLOAD%" echo error=Configured phase upload file was not created by the dispatcher.
  >>"%FALLBACK_UPLOAD%" echo repo_root=%CD%
  if exist "%BOOTSTRAP_ERROR%" (
    >>"%FALLBACK_UPLOAD%" echo.
    >>"%FALLBACK_UPLOAD%" echo ===== DISPATCHER BOOTSTRAP ERROR =====
    type "%BOOTSTRAP_ERROR%" >>"%FALLBACK_UPLOAD%"
    >>"%FALLBACK_UPLOAD%" echo ===== END DISPATCHER BOOTSTRAP ERROR =====
  )
  set "UPLOAD_FILE=%FALLBACK_UPLOAD%"
  >"%UPLOAD_PATH_FILE%" echo !UPLOAD_FILE!
)

echo.
if "%RC%"=="0" (
  echo [DONE] Current GOLD_ML_V1 action completed successfully.
) else (
  echo [FAIL] Exit code: %RC%
)

echo.
echo Upload this file to ChatGPT:
echo !UPLOAD_FILE!
echo.
echo The output folder will now open with the file selected.
start "" explorer.exe /select,"!UPLOAD_FILE!" >nul 2>nul

echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%

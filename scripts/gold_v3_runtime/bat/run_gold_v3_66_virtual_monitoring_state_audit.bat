@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 66 virtual monitoring state audit-only runner.
REM Builds virtual monitoring state only.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\65_rolling_prior_60d_q70_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\65_rolling_prior_60d_q70_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\65_rolling_prior_60d_q70_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\65_rolling_prior_60d_q70_state_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage65 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE65_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\65_rolling_prior_60d_q70_state_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\66_virtual_monitoring_state_audit_only"
for %%I in ("%STAGE65_DIR%") do set "STAGE65_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE65_DIR%\gold_v3_65_q70_state_summary.json" (
    echo [ERROR] Stage65 summary not found.
    pause
    exit /b 1
)
if not exist "%STAGE65_DIR%\gold_v3_65_m15_asof_q70_state.csv" (
    echo [ERROR] Stage65 M15 asof Q70 state not found.
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 66 VIRTUAL MONITORING STATE AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE65_DIR=%STAGE65_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo Builds virtual monitoring state only. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_66_virtual_monitoring_state_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage65-dir "%STAGE65_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 66 virtual monitoring state failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 66 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_66_PASTE_ME_VIRTUAL_MONITORING_SUMMARY.txt
echo.
pause
exit /b 0

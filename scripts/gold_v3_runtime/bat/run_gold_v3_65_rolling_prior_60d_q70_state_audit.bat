@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 65 rolling prior-60D Q70 state audit-only runner.
REM CSV contract: open/in-progress candles are not written to CSV.
REM No MT5 orders, no Discord, no AI API, no live hook, no final signal.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\FX_OUTPUTS\gold_v3\64_m15_m5_alignment_state_builder_audit_only" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3\64_m15_m5_alignment_state_builder_audit_only" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\FX_OUTPUTS\gold_v3\64_m15_m5_alignment_state_builder_audit_only" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\FX_OUTPUTS\gold_v3\64_m15_m5_alignment_state_builder_audit_only" set "CANDLE_DIR=%REPO_ROOT%"
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Stage64 output directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "STAGE64_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\64_m15_m5_alignment_state_builder_audit_only"
set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\65_rolling_prior_60d_q70_state_audit_only"
for %%I in ("%STAGE64_DIR%") do set "STAGE64_DIR=%%~fI"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%STAGE64_DIR%\gold_v3_64_alignment_summary.json" (
    echo [ERROR] Stage64 summary not found.
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_h4.csv" (
    echo [ERROR] goldsharp_h4.csv not found in CANDLE_DIR.
    echo CANDLE_DIR=%CANDLE_DIR%
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_m15.csv" (
    echo [ERROR] goldsharp_m15.csv not found in CANDLE_DIR.
    echo CANDLE_DIR=%CANDLE_DIR%
    pause
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 65 ROLLING PRIOR 60D Q70 STATE AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo STAGE64_DIR=%STAGE64_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.
echo CSV contract: open/in-progress candles are not written to CSV.
echo Computes H4 rolling prior-60D Q70 state. No live enablement.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_65_rolling_prior_60d_q70_state_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --stage64-dir "%STAGE64_DIR%" ^
  --output-dir "%OUTPUT_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 65 rolling prior-60D Q70 state failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 65 outputs written to:
echo %OUTPUT_DIR%
echo.
echo Paste this file if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_65_PASTE_ME_Q70_STATE_SUMMARY.txt
echo.
pause
exit /b 0

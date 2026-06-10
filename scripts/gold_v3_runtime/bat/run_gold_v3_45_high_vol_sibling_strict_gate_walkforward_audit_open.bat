@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 45 OPEN asof audit-only runner.
REM Use this from VSCode when command-line options cannot be passed.
REM This BAT only launches the audit/backtest script in HTF_ASOF=open mode.
REM It does NOT send MT5 orders, does NOT enable Discord, and does NOT create final signals.

set "SCRIPT_DIR=%~dp0"
REM BAT location: scripts\gold_v3_runtime\bat
REM Repo root: BAT\..\..\..
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
set "HTF_ASOF=open"

REM Expected local layout: Files\xauusd-signal-lab-clean\xauusd-signal-lab\scripts\gold_v3_runtime\bat
REM Candle CSVs live under Files, so repo root\..\.. should be Files.
if exist "%REPO_ROOT%\..\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\Files\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\Files"
)
if "%CANDLE_DIR%"=="" (
    if exist "%REPO_ROOT%\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%"
)

if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not find goldsharp_m15.csv near repo layout.
    pause
    exit /b 1
)

REM Normalize CANDLE_DIR so Python/Pandas does not receive a path containing .. segments.
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

if not exist "%CANDLE_DIR%\goldsharp_m5.csv" (
    echo [ERROR] Missing %CANDLE_DIR%\goldsharp_m5.csv
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_m15.csv" (
    echo [ERROR] Missing %CANDLE_DIR%\goldsharp_m15.csv
    pause
    exit /b 1
)
if not exist "%CANDLE_DIR%\goldsharp_h4.csv" (
    echo [ERROR] Missing %CANDLE_DIR%\goldsharp_h4.csv
    pause
    exit /b 1
)

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\45_high_vol_sibling_strict_gate_walkforward_audit_only_OPEN"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if not exist "%OUTPUT_DIR%" (
    echo [ERROR] Could not create OUTPUT_DIR:
    echo %OUTPUT_DIR%
    pause
    exit /b 1
)

echo [GOLD V3 45 AUDIT ONLY - OPEN HTF ASOF]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo OUTPUT_DIR=%OUTPUT_DIR%
echo HTF_ASOF=%HTF_ASOF%
echo.
echo This is audit-only. No MT5 order, no Discord, no live/final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py" ^
  --candle-dir "%CANDLE_DIR%" ^
  --output-dir "%OUTPUT_DIR%" ^
  --start-jst 2026-01-01 ^
  --htf-asof "%HTF_ASOF%" ^
  --hv-rolling-days 60 ^
  --hv-quantile 0.70 ^
  --health-window 30 ^
  --health-min-history 20 ^
  --strict-pf-threshold 1.10 ^
  --strict-loss-streak-lt 3 ^
  --run-walkforward

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] GOLD V3 45 OPEN audit-only runner failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 45 OPEN audit-only outputs written to:
echo %OUTPUT_DIR%
echo.
echo Review these first:
echo - gold_v3_45_hv_sibling_gate_experiment_summary.csv
echo - gold_v3_45_hv_sibling_rolling_walkforward_monthly_summary.csv
echo - GOLD_V3_45_HIGH_VOL_SIBLING_STRICT_GATE_AUDIT_ONLY_REPORT.md
echo.
pause
exit /b 0

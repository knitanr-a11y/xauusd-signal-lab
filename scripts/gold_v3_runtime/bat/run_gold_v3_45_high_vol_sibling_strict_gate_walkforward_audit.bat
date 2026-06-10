@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 45 high-vol sibling strict rolling health gate walk-forward audit-only runner.
REM This BAT only launches a Python audit/backtest script.
REM It does NOT send MT5 orders, does NOT enable Discord, and does NOT create final signals.

set "SCRIPT_DIR=%~dp0"
REM BAT location: scripts\gold_v3_runtime\bat
REM Repo root: BAT\..\..\..
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR=%~1"
set "HTF_ASOF=%~2"

if "%HTF_ASOF%"=="" set "HTF_ASOF=closed"

if "%CANDLE_DIR%"=="" (
    REM Expected local layout: Files\xauusd-signal-lab-clean\xauusd-signal-lab\scripts\gold_v3_runtime\bat
    REM Candle CSVs live under Files, so repo root\..\.. should be Files.
    if exist "%REPO_ROOT%\..\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\..\.."
)
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
    echo [ERROR] Could not find goldsharp_m15.csv. Pass the MT5 Files directory as the first argument.
    echo Example: %~nx0 "C:\path\to\MQL5\Files" closed
    pause
    exit /b 1
)

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

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\45_high_vol_sibling_strict_gate_walkforward_audit_only"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [GOLD V3 45 AUDIT ONLY]
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
    echo [FAILED] GOLD V3 45 audit-only runner failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 45 audit-only outputs written to:
echo %OUTPUT_DIR%
echo.
echo Review these first:
echo - gold_v3_45_hv_sibling_gate_experiment_summary.csv
echo - gold_v3_45_hv_sibling_rolling_walkforward_monthly_summary.csv
echo - GOLD_V3_45_HIGH_VOL_SIBLING_STRICT_GATE_AUDIT_ONLY_REPORT.md
echo.
pause
exit /b 0

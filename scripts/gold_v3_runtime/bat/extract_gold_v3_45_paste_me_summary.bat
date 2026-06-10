@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 45 compact paste-me summary extractor.
REM This does not run a backtest. It extracts small review files from existing Stage45 outputs.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
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
    echo [ERROR] Could not locate Files directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

set "OUTPUT_DIR=%CANDLE_DIR%\FX_OUTPUTS\gold_v3\45_high_vol_sibling_strict_gate_walkforward_audit_only"
for %%I in ("%OUTPUT_DIR%") do set "OUTPUT_DIR=%%~fI"

if not exist "%OUTPUT_DIR%\gold_v3_45_hv_sibling_strict_gate_summary.json" (
    echo [ERROR] Stage45 closed output not found:
    echo %OUTPUT_DIR%\gold_v3_45_hv_sibling_strict_gate_summary.json
    echo Run run_gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.bat first.
    pause
    exit /b 1
)

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_45_extract_paste_me_summary.py" ^
  --output-dir "%OUTPUT_DIR%" ^
  --mode-label closed_valid

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo [FAILED] paste-me summary extraction failed with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] Paste this file content into chat if upload limit is reached:
echo %OUTPUT_DIR%\gold_v3_45_PASTE_ME_REVIEW_SUMMARY.txt
echo.
pause
exit /b 0

@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 88 signal candidate normalization and condition coverage audit-only.
REM Normalizes 44 expanded rows into 8 base candidates plus HV expansions.
REM Does not guess missing conditions. No Discord, no MT5, no AI API, no final signal.

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
    if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%\.."
)
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Files directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

echo [GOLD V3 88 SIGNAL CANDIDATE NORMALIZATION AND CONDITION COVERAGE AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo Normalizes candidate catalog and measures condition coverage.
echo Missing conditions are marked unresolved, not guessed.
echo This does NOT append ledger, place orders, send Discord, call AI API, or enable final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_88_signal_candidate_normalization_and_condition_coverage_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 88 signal candidate normalization ended with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 88 signal candidate normalization completed.
echo Paste the PASTE_ME path printed above.
echo.
pause
exit /b 0

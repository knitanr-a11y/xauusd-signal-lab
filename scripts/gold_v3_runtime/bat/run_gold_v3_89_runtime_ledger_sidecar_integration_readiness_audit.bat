@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 89 runtime ledger sidecar integration readiness audit-only.
REM Checks if Stage85/86 can be safely planned after Stage80->76->79.
REM Does not patch Stage80. Does not enable autorun. No Discord, MT5, AI API, live hook, or final signal.

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

echo [GOLD V3 89 RUNTIME LEDGER SIDECAR INTEGRATION READINESS AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo Checks readiness for future Stage80 ledger sidecar integration.
echo This does NOT patch Stage80, enable autorun, append ledger, place orders, send Discord, call AI API, or enable final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_89_runtime_ledger_sidecar_integration_readiness_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 89 runtime ledger sidecar readiness ended with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 89 runtime ledger sidecar readiness completed.
echo Paste the PASTE_ME path printed above.
echo.
pause
exit /b 0

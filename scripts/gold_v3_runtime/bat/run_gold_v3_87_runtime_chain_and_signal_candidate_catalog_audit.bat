@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 87 runtime chain and signal candidate catalog audit-only.
REM Generates candidate bullet catalog from GOLD V3 Stage69/68 artifacts when available.
REM No durable ledger append. No Discord send, no MT5 order, no AI API, no live hook, no final signal.

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

echo [GOLD V3 87 RUNTIME CHAIN AND SIGNAL CANDIDATE CATALOG AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo Generates candidate catalog bullets from Stage69/68 GOLD V3 artifacts.
echo If candidate source CSV is missing, this stage will BLOCK instead of guessing.
echo This does NOT append ledger, place orders, send Discord, call AI API, or enable final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_87_runtime_chain_and_signal_candidate_catalog_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 87 runtime chain and signal candidate catalog ended with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 87 runtime chain and signal candidate catalog completed.
echo Paste the PASTE_ME path printed above.
echo.
pause
exit /b 0

@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 86 trade review ledger append guard audit-only.
REM Guards durable trade ledger from NO_SIGNAL/heartbeat/error rows and incomplete/unconfirmed records.
REM No durable append. No Discord send, no MT5 order, no AI API, no live hook, no final signal.

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

echo [GOLD V3 86 TRADE REVIEW LEDGER APPEND GUARD AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo Guards durable trade ledger append policy.
echo This does NOT append ledger, place orders, send Discord, call AI API, or enable final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_86_trade_review_ledger_append_guard_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 86 trade review ledger append guard ended with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 86 trade review ledger append guard completed.
echo Paste the PASTE_ME path printed above.
echo.
pause
exit /b 0

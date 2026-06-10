@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 82 runtime doc sync and operator checklist audit-only.
REM Verifies manual/checklist references and local Stage80 READY state.
REM No Discord send, no MT5 order, no AI API, no live hook, no final signal.

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

echo [GOLD V3 82 RUNTIME DOC SYNC AND OPERATOR CHECKLIST AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo Verifies runtime manual/checklist and Stage80 auto support bundle readiness.
echo No MT5 orders, no Discord, no AI API, no live hook, no final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_82_runtime_doc_sync_and_operator_checklist_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 82 runtime doc sync ended with errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 82 runtime doc sync completed.
echo Paste the PASTE_ME path printed above.
echo.
pause
exit /b 0

@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 79 immutable runtime output policy audit-only.
REM Creates a run_id-based immutable snapshot of Stage76 runtime evidence.
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

echo [GOLD V3 79 IMMUTABLE RUNTIME OUTPUT POLICY AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo Creates a new immutable run_id snapshot under:
echo %CANDLE_DIR%\FX_OUTPUTS\gold_v3\runtime_immutable\YYYYMMDD\RUN_ID
echo.
echo No MT5 orders, no Discord, no AI API, no live hook, no final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_79_immutable_runtime_output_policy_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 79 immutable runtime output policy ended with errorlevel %ERR%.
    echo Check console output above for the newly-created run_dir if any.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 79 immutable snapshot created.
echo The exact PASTE_ME path was printed above by the Python runner.
echo.
pause
exit /b 0

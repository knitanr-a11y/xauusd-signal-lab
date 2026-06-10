@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 81 compact support bundle audit-only.
REM Creates one small upload_first.txt so the user does not need to upload huge logs.
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

echo [GOLD V3 81 COMPACT SUPPORT BUNDLE AUDIT ONLY]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.
echo This creates one small upload_first.txt for troubleshooting.
echo Do not upload huge event/timing CSV files unless requested.
echo No MT5 orders, no Discord, no AI API, no live hook, no final signal.
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_81_compact_support_bundle_audit.py" ^
  --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [BLOCKED/FAILED] GOLD V3 81 compact support bundle ended with errorlevel %ERR%.
    echo Check console output above for bundle path if any.
    pause
    exit /b %ERR%
)

echo.
echo [DONE] GOLD V3 81 compact support bundle created.
echo Upload/paste the upload_first.txt path printed above.
echo.
pause
exit /b 0

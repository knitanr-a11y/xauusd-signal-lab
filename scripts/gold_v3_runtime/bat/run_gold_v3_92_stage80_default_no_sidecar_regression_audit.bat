@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

set "CANDLE_DIR="
if exist "%REPO_ROOT%\..\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\..\.."
if "%CANDLE_DIR%"=="" if exist "%REPO_ROOT%\..\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\.."
if "%CANDLE_DIR%"=="" if exist "%REPO_ROOT%\Files\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%\Files"
if "%CANDLE_DIR%"=="" if exist "%REPO_ROOT%\goldsharp_m15.csv" set "CANDLE_DIR=%REPO_ROOT%"
if "%CANDLE_DIR%"=="" if exist "%REPO_ROOT%\..\FX_OUTPUTS\gold_v3" set "CANDLE_DIR=%REPO_ROOT%\.."
if "%CANDLE_DIR%"=="" (
    echo [ERROR] Could not locate Files directory.
    pause
    exit /b 1
)
for %%I in ("%CANDLE_DIR%") do set "CANDLE_DIR=%%~fI"

echo [GOLD V3 92 DEFAULT NO-SIDECAR REGRESSION]
echo REPO_ROOT=%REPO_ROOT%
echo CANDLE_DIR=%CANDLE_DIR%
echo.

python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_92_stage80_default_no_sidecar_regression_audit.py" --candle-dir "%CANDLE_DIR%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [FAILED] errorlevel %ERR%.
    pause
    exit /b %ERR%
)

echo.
echo [DONE]
echo Paste:
echo %CANDLE_DIR%\FX_OUTPUTS\gold_v3\92c\paste_me.txt
echo.
pause
exit /b 0

@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 119 JUNE CURRENT PERIOD AUDIT
echo ============================================================
echo MODE: audit-only review
echo Period: 2026-06-01 to 2026-07-01 exclusive
echo ============================================================

echo [1/4] Working directory set
echo   %CD%
echo.
echo [2/4] Starting Python audit script
py -3 scripts\gold_v3_runtime\gold_v3_119_june_current_period_backtest_audit.py
echo.
if errorlevel 1 goto err

echo [3/4] Python script finished
echo.
echo [4/4] Output location
echo   FX_OUTPUTS\gold_v3\119
echo.
echo DONE
pause
exit /b 0

:err
echo [3/4] Python script finished with error
echo.
echo [4/4] Output location
echo   FX_OUTPUTS\gold_v3\119
echo.
echo FAILED - check FX_OUTPUTS\gold_v3\119\paste_me.txt
pause
exit /b 1

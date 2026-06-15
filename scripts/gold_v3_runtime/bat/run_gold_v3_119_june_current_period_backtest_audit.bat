@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 119 JUNE 01-15 PERIOD AUDIT
echo ============================================================
echo MODE: audit-only review
echo Period: 2026-06-01 to 2026-06-16 exclusive
echo Requirement: 107L input max entry_dt must reach 2026-06-15
echo ============================================================

echo [1/4] Working directory set
echo   %CD%
echo.
echo [2/4] Starting Python audit script
py -3 scripts\gold_v3_runtime\gold_v3_119_june_current_period_backtest_audit.py --start 2026-06-01 --end-exclusive 2026-06-16 --require-min-input-max-entry-dt 2026-06-15
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

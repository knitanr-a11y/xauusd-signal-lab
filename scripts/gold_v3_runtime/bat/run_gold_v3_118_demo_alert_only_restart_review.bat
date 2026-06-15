@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 118 DEMO ALERT-ONLY RESTART REVIEW
echo ============================================================
echo MODE: audit-only review. This BAT does not start the demo loop.
echo Recommended demo loop remains:
echo   scripts\gold_v3_runtime\bat\run_gold_v3_116_115_full_loop.bat
echo ============================================================

echo [1/4] Working directory set
echo   %CD%
echo.
echo [2/4] Review target BAT
echo   scripts\gold_v3_runtime\bat\run_gold_v3_116_115_full_loop.bat
echo.
echo [3/4] Manual review required
echo   Confirm alert-only, NO_SIGNAL no Discord, no execution path, closed CSV contract.
echo.
echo [4/4] Output location
echo   FX_OUTPUTS\gold_v3\118

echo.
echo Stage118 BAT is a placeholder/review helper only.
echo To start demo alert-only monitoring, explicit user approval is still required.
pause
exit /b 0

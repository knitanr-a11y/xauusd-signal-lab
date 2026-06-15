@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 121 UPSTREAM 107L COVERAGE DIAGNOSIS AUDIT
echo ============================================================
echo MODE: audit-only review
echo Target: 2026-06-15
echo ============================================================

echo [1/4] Working directory set
echo   %CD%
echo.
echo [2/4] Starting Python audit script
py -3 scripts\gold_v3_runtime\gold_v3_121_upstream_107l_coverage_diagnosis_audit.py --target 2026-06-15
if errorlevel 1 goto err

echo.
echo [3/4] Python script finished
echo.
echo [4/4] Output location
echo   FX_OUTPUTS\gold_v3\121\paste_me.txt
echo.
echo DONE
pause
exit /b 0

:err
echo.
echo [3/4] Python script finished with error
echo.
echo [4/4] Output location
echo   FX_OUTPUTS\gold_v3\121
pause
exit /b 1

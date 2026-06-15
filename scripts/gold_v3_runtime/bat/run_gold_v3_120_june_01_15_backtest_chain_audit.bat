@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 120 JUNE 01-15 BACKTEST CHAIN AUDIT
echo ============================================================
echo MODE: audit-only review
echo Period: 2026-06-01 to 2026-06-16 exclusive
echo Requirement: 107L input max entry_dt must reach 2026-06-15
echo ============================================================

echo [1/6] Working directory set
echo   %CD%
echo.
echo [2/6] Shadow rerun Stage117J from current 107L and 107M inputs
py -3 scripts\gold_v3_runtime\gold_v3_117j_shadow_107q_rerun_audit.py
if errorlevel 1 goto err

echo.
echo [3/6] Rebuild Stage117L June F002 removed detail
py -3 scripts\gold_v3_runtime\gold_v3_117l_june_removed_8_detail_review.py
if errorlevel 1 goto err

echo.
echo [4/6] Rebuild Stage117M review-only restore comparison
py -3 scripts\gold_v3_runtime\gold_v3_117m_june_restore_policy_comparison.py
if errorlevel 1 goto err

echo.
echo [5/6] Run Stage119 period audit 2026-06-01 through 2026-06-15
py -3 scripts\gold_v3_runtime\gold_v3_119_june_current_period_backtest_audit.py --start 2026-06-01 --end-exclusive 2026-06-16 --require-min-input-max-entry-dt 2026-06-15
if errorlevel 1 goto err

echo.
echo [6/6] Output location
echo   FX_OUTPUTS\gold_v3\119\paste_me.txt
echo.
echo DONE
pause
exit /b 0

:err
echo.
echo FAILED during Stage120 June 01-15 audit chain.
echo Check latest paste_me files under:
echo   FX_OUTPUTS\gold_v3\117j
echo   FX_OUTPUTS\gold_v3\117l
echo   FX_OUTPUTS\gold_v3\117m
echo   FX_OUTPUTS\gold_v3\119
pause
exit /b 1

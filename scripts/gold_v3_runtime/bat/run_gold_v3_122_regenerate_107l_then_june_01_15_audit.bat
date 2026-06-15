@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo ============================================================
echo GOLD V3 122 REGENERATE 107L THEN JUNE 01-15 AUDIT
echo ============================================================
echo MODE: audit-only review
echo Target period: 2026-06-01 to 2026-06-16 exclusive
echo Requirement: refreshed 107L max entry_dt must reach 2026-06-15
echo ============================================================

echo [1/8] Working directory set
echo   %CD%
echo.

echo [2/8] Rebuild Stage107L from current Stage107K2 inputs
py -3 scripts\gold_v3_runtime\gold_v3_107l_regime_rehydration_and_health_gate_audit.py
if errorlevel 1 goto err

echo.
echo [3/8] Rebuild Stage107M from refreshed Stage107L
py -3 scripts\gold_v3_runtime\gold_v3_107m_problem_regime_loss_trim_audit.py
if errorlevel 1 goto err

echo.
echo [4/8] Shadow rerun Stage117J from refreshed 107L and 107M
py -3 scripts\gold_v3_runtime\gold_v3_117j_shadow_107q_rerun_audit.py
if errorlevel 1 goto err

echo.
echo [5/8] Rebuild Stage117L F002 removed detail
py -3 scripts\gold_v3_runtime\gold_v3_117l_june_removed_8_detail_review.py
if errorlevel 1 goto err

echo.
echo [6/8] Rebuild Stage117M review-only restore comparison
py -3 scripts\gold_v3_runtime\gold_v3_117m_june_restore_policy_comparison.py
if errorlevel 1 goto err

echo.
echo [7/8] Run Stage119 period audit through 2026-06-15
py -3 scripts\gold_v3_runtime\gold_v3_119_june_current_period_backtest_audit.py --start 2026-06-01 --end-exclusive 2026-06-16 --require-min-input-max-entry-dt 2026-06-15
if errorlevel 1 goto err

echo.
echo [8/8] Output location
echo   FX_OUTPUTS\gold_v3\119\paste_me.txt
echo.
echo DONE
pause
exit /b 0

:err
echo.
echo FAILED during Stage122 regenerate-then-period-audit chain.
echo Check latest paste_me files under:
echo   FX_OUTPUTS\gold_v3\107lc
echo   FX_OUTPUTS\gold_v3\107mc
echo   FX_OUTPUTS\gold_v3\117j
echo   FX_OUTPUTS\gold_v3\117l
echo   FX_OUTPUTS\gold_v3\117m
echo   FX_OUTPUTS\gold_v3\119
pause
exit /b 1

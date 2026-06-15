@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo GOLD V3 124
py -3 scripts\gold_v3_runtime\gold_v3_107k2_direct_regime_balanced_adaptive_score_audit.py
if errorlevel 1 goto err

call scripts\gold_v3_runtime\bat\run_gold_v3_122_regenerate_107l_then_june_01_15_audit.bat
if errorlevel 1 goto err

echo DONE
pause
exit /b 0

:err
echo FAILED
pause
exit /b 1

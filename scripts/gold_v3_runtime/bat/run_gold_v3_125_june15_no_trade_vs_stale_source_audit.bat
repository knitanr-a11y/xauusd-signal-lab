@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo GOLD V3 125
py -3 scripts\gold_v3_runtime\gold_v3_125_june15_no_trade_vs_stale_source_audit.py
if errorlevel 1 goto err

echo DONE. Check FX_OUTPUTS\gold_v3\125\paste_me.txt
pause
exit /b 0

:err
echo BLOCKED. Check FX_OUTPUTS\gold_v3\125\paste_me.txt
pause
exit /b 1

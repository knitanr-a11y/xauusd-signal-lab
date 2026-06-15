@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"

echo GOLD V3 128 NO-TRADE-AWARE JUNE PERIOD AUDIT
py -3 scripts\gold_v3_runtime\gold_v3_128_june_period_audit_no_trade_aware.py --mt5-files-dir "%MT5_FILES%" --start 2026-06-01 --end-exclusive 2026-06-16 --require-min-upstream-max-entry-dt 2026-06-15
if errorlevel 1 goto err

echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\128\paste_me.txt
pause
exit /b 0

:err
echo BLOCKED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\128\paste_me.txt
pause
exit /b 1

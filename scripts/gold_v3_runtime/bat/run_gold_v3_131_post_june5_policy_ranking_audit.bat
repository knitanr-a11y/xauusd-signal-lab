@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"

echo GOLD V3 131 POST-JUNE5 POLICY RANKING AUDIT
py -3 scripts\gold_v3_runtime\gold_v3_131_post_june5_policy_ranking_audit.py --mt5-files-dir "%MT5_FILES%" --start-after "2026-06-05 15:15:00" --end-exclusive 2026-06-16 --min-rows 10 --min-unique-entry-times 3
if errorlevel 1 goto err

echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\131\paste_me.txt
pause
exit /b 0

:err
echo FAILED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\131\paste_me.txt
pause
exit /b 1

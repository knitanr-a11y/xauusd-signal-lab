@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"

echo GOLD V3 135 CHAMPION STALL DAILY ROUTE REPLAY AUDIT
py -3 scripts\gold_v3_runtime\gold_v3_135_champion_stall_daily_route_replay_audit.py --mt5-files-dir "%MT5_FILES%" --start 2025-07-01 --end-exclusive 2026-06-16 --stall-days 3
if errorlevel 1 goto err

echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\135\paste_me.txt
pause
exit /b 0

:err
echo FAILED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\135\paste_me.txt
pause
exit /b 1

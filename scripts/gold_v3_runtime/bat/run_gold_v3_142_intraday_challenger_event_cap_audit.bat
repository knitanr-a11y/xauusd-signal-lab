@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
echo GOLD V3 142 INTRADAY CHALLENGER EVENT CAP AUDIT
echo Progress is printed as config X/60 and also written to:
echo %MT5_FILES%\FX_OUTPUTS\gold_v3\142\progress.txt
py -3 scripts\gold_v3_runtime\gold_v3_142_intraday_challenger_event_cap_audit.py --mt5-files-dir "%MT5_FILES%" --start 2025-07-01 --end-exclusive 2026-06-16 --min-history-days 30
echo Check %MT5_FILES%\FX_OUTPUTS\gold_v3\142\paste_me.txt
pause

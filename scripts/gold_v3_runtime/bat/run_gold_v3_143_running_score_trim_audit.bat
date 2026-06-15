@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
echo GOLD V3 143 RUNNING SCORE TRIM AUDIT
echo Progress is printed as config X/N and also written to:
echo %MT5_FILES%\FX_OUTPUTS\gold_v3\143\progress.txt
py -3 scripts\gold_v3_runtime\gold_v3_143_running_score_trim_audit.py --mt5-files-dir "%MT5_FILES%" --start 2025-07-01 --end-exclusive 2026-06-16 --min-history-days 30 --min-history-events 30
echo Check %MT5_FILES%\FX_OUTPUTS\gold_v3\143\paste_me.txt
pause

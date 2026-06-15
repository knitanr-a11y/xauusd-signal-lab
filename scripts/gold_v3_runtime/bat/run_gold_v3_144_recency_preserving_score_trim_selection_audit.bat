@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
echo GOLD V3 144 RECENCY-PRESERVING SCORE TRIM SELECTION AUDIT
echo Progress is printed as config X/N and also written to:
echo %MT5_FILES%\FX_OUTPUTS\gold_v3\144\progress.txt
py -3 scripts\gold_v3_runtime\gold_v3_144_recency_preserving_score_trim_selection_audit.py --mt5-files-dir "%MT5_FILES%" --min-route-events 150 --min-challenger-events 50 --min-june-route-events 5 --min-june-worst 1
if errorlevel 1 goto err
echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\144\paste_me.txt
pause
exit /b 0
:err
echo FAILED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\144\paste_me.txt
pause
exit /b 1

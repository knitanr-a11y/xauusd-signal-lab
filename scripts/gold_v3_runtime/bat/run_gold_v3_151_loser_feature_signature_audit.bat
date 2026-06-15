@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
echo GOLD V3 151 LOSER FEATURE SIGNATURE AUDIT
echo Progress is printed as config X/1 and also written to:
echo %MT5_FILES%\FX_OUTPUTS\gold_v3\151\progress.txt
py -3 scripts\gold_v3_runtime\gold_v3_151_loser_feature_signature_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err
echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\151\paste_me.txt
pause
exit /b 0
:err
echo FAILED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\151\paste_me.txt
pause
exit /b 1

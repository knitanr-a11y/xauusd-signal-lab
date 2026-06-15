@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
echo GOLD V3 160 CURRENT PLUS ADDON UNION AUDIT
echo Progress is printed as config X/N and also written to:
echo %MT5_FILES%\FX_OUTPUTS\gold_v3\160\progress.txt
py -3 scripts\gold_v3_runtime\gold_v3_160_current_plus_addon_union_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err
echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\160\paste_me.txt
pause
exit /b 0
:err
echo FAILED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\160\paste_me.txt
pause
exit /b 1

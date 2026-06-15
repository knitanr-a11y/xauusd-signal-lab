@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"

echo GOLD V3 138A LITE CHALLENGER FACTOR MATRIX AUDIT WITH PROGRESS
echo Progress will be printed as config X/64 and written to:
echo %MT5_FILES%\FX_OUTPUTS\gold_v3\138a\progress.txt

py -3 scripts\gold_v3_runtime\gold_v3_138a_lite_challenger_factor_matrix_audit.py --mt5-files-dir "%MT5_FILES%" --start 2025-07-01 --end-exclusive 2026-06-16 --min-history-days 30
if errorlevel 1 goto err

echo DONE. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\138a\paste_me.txt
pause
exit /b 0

:err
echo FAILED. Check %MT5_FILES%\FX_OUTPUTS\gold_v3\138a\paste_me.txt
echo If the process was interrupted, check %MT5_FILES%\FX_OUTPUTS\gold_v3\138a\progress.txt
pause
exit /b 1

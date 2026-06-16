@echo off
setlocal

REM GOLD V3 Stage231 - MT5 demo order reconciliation audit.
REM Read-only: no new order, no close, no position modification.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_231_mt5_demo_order_reconciliation_audit.py

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage231 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\231\paste_me.txt

endlocal
pause
exit /b %EXITCODE%

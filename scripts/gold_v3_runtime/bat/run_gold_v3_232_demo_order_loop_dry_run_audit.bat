@echo off
setlocal

REM GOLD V3 Stage232 - Demo order loop dry-run audit.
REM No order_send. No order placement. No close/modify.
REM Refresh Stage227 runtime queue first, then evaluate queue once.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_232_demo_order_loop_dry_run_audit.py --refresh-stage227 --cycles 1

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage232 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\232\paste_me.txt

endlocal
pause
exit /b %EXITCODE%

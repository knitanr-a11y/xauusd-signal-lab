@echo off
setlocal

REM GOLD V3 Stage226 - demo Discord alert-only loop restart local.
REM CSV read timing: every minute 00 seconds + 5 seconds.
REM MT5 order, real account, payload activation, live hook, final live, autotrade, NO_SIGNAL notification: not allowed.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_226_demo_discord_alert_only_loop_restart_local.py

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage226 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\226\paste_me.txt

endlocal
pause
exit /b %EXITCODE%
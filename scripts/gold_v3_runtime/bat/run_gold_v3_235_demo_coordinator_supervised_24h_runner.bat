@echo off
setlocal

REM GOLD V3 Stage235 - DEMO coordinator supervised 24H runner.
REM Calls Stage234 once per minute for max 1440 cycles.
REM Stage235 itself does not directly call Discord webhook or mt5.order_send.
REM This is bounded 24-hour DEMO supervision, not final live and not unbounded autotrade.

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_235_demo_coordinator_supervised_24h_runner.py --cycles 1440 --delay-seconds 5

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage235 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\235\paste_me.txt

echo.
echo To stop Stage235 safely, create:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\KILL_SWITCH_STAGE235.txt

echo.
echo Stage234 kill switch also works:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\KILL_SWITCH_STAGE234.txt

echo.
echo Stage233 order-loop kill switch also works:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\KILL_SWITCH_STAGE233.txt

endlocal
pause
exit /b %EXITCODE%

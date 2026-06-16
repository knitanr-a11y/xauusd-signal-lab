@echo off
setlocal

REM GOLD V3 Stage233 - Demo order loop SCALP/DAYTRADE 0.01 lot.
REM User-approved DEMO order loop only.
REM Constraints:
REM - DEMO account only
REM - GOLD# only
REM - SCALP 0.01 lot, DAYTRADE 0.01 lot
REM - ORDER_FILLING_IOC
REM - TP/SL required
REM - one order per signal_id
REM - SCALP max 1 open position
REM - DAYTRADE max 1 open position
REM - total max 2 Stage233 positions
REM - no real account, no final live, no payload activation, no NO_SIGNAL order
REM - bounded loop: max 60 cycles, each minute boundary + 5 seconds
REM Kill switch file:
REM %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\KILL_SWITCH_STAGE233.txt

cd /d "%~dp0\..\..\.."

python scripts\gold_v3_runtime\gold_v3_233_demo_order_loop_scalp_daytrade_001lot.py --refresh-stage227 --wait-boundary --delay-seconds 5 --cycles 60

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage233 exited with code %EXITCODE%.
echo Paste this file into the next chat:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\233\paste_me.txt

echo.
echo To stop the loop safely, create this file before or during execution:
echo %%APPDATA%%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\KILL_SWITCH_STAGE233.txt

endlocal
pause
exit /b %EXITCODE%

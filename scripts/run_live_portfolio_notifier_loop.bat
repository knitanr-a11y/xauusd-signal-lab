@echo off
setlocal EnableExtensions

REM ============================================================================
REM GOLD/BTC live portfolio notifier loop
REM
REM - GOLD: run_live_gold_notifier_from_csv.py via portfolio wrapper
REM - BTC : run_live_btc_mtf_spread_filtered_notifier_from_csv.py via portfolio wrapper
REM - Timing: run at every minute xx:02 to avoid MT5 CSV write timing at xx:00
REM - Stop: Ctrl+C, then Y
REM ============================================================================

cd /d "%~dp0\.."

set "GOLD_M15_CSV=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m15.csv"
set "GOLD_H1_CSV=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_h1.csv"
set "BTC_M5_CSV=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m5.csv"
set "BTC_M15_CSV=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv"
set "BTC_H1_CSV=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_h1.csv"
set "BTC_H4_CSV=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_h4.csv"

set "HISTORY_CSV=data\results\gold_btc_final_portfolio_trades.csv"
set "RUN_SECOND=2"

echo ============================================================================
echo GOLD/BTC live portfolio notifier loop
echo Project: %CD%
echo Timing: every minute at xx:0%RUN_SECOND%
echo Stop: Ctrl+C, then Y
echo ============================================================================

:LOOP
call :WAIT_UNTIL_RUN_SECOND

echo.
echo ============================================================================
echo Run started: %DATE% %TIME%
echo ============================================================================

python scripts\run_live_portfolio_notifier_from_csv.py --gold-m15-csv "%GOLD_M15_CSV%" --gold-h1-csv "%GOLD_H1_CSV%" --btc-m5-csv "%BTC_M5_CSV%" --btc-m15-csv "%BTC_M15_CSV%" --btc-h1-csv "%BTC_H1_CSV%" --btc-h4-csv "%BTC_H4_CSV%" --history-csv "%HISTORY_CSV%" --gold-scan-recent-bars 60 --btc-scan-recent-m5-bars 60 --btc-scan-recent-m15-bars 20 --btc-spread-mode csv_mode --btc-spread-source m5 --btc-point-size 0.01 --btc-pip-size 10 --enable-ai-review --send-discord

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Run finished: %DATE% %TIME%
echo Exit code: %EXIT_CODE%

if not "%EXIT_CODE%"=="0" (
    echo WARNING: portfolio notifier returned a non-zero exit code.
    echo The loop will continue at the next xx:0%RUN_SECOND% slot.
)

goto LOOP

:WAIT_UNTIL_RUN_SECOND
for /f "tokens=1-4 delims=:. ," %%a in ("%TIME%") do (
    set /a "NOW_SEC=1%%c-100"
)

set /a "WAIT_SEC=RUN_SECOND-NOW_SEC"
if %WAIT_SEC% LEQ 0 set /a "WAIT_SEC=WAIT_SEC+60"

echo Waiting %WAIT_SEC% seconds until next xx:0%RUN_SECOND% slot... Current time: %TIME%
timeout /t %WAIT_SEC% /nobreak >nul
exit /b 0

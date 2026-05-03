@echo off
setlocal EnableExtensions

REM ============================================================================
REM GOLD/BTC live portfolio notifier loop
REM
REM - GOLD: run_live_gold_notifier_from_csv.py via portfolio wrapper
REM - BTC : run_live_btc_mtf_spread_filtered_notifier_from_csv.py via portfolio wrapper
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
set "LOOP_SECONDS=60"

echo ============================================================================
echo GOLD/BTC live portfolio notifier loop
echo Project: %CD%
echo Interval seconds: %LOOP_SECONDS%
echo Stop: Ctrl+C, then Y
echo ============================================================================

:LOOP
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
    echo The loop will continue after the wait interval.
)

echo Waiting %LOOP_SECONDS% seconds...
timeout /t %LOOP_SECONDS% /nobreak >nul
goto LOOP

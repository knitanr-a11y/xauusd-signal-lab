@echo off
setlocal EnableExtensions

REM ============================================================================
REM GOLD/BTC live portfolio notifier loop
REM
REM - GOLD: confirmed-time M15/H1 join via portfolio wrapper
REM - BTC : confirmed-time M5/M15/H1/H4 join + spread-filtered notifier via portfolio wrapper
REM - Timing: run at every minute xx:01 after MQL5 CSV export at xx:00
REM - Bar offset: 0 because MQL5 CSV exports confirmed/closed bars only
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
set "RUN_SECOND=1"

echo ============================================================================
echo GOLD/BTC live portfolio notifier loop ^(confirmed-time MTF join^)
echo Project: %CD%
echo Timing: every minute at xx:01
echo Bar offset: 0 ^(MQL5 CSV confirmed bars only^)
echo Stop: Ctrl+C, then Y
echo ============================================================================

:LOOP
call :WAIT_UNTIL_RUN_SECOND

echo.
echo ============================================================================
echo Run started: %DATE% %TIME%
echo ============================================================================

python scripts\run_live_portfolio_confirmed_notifier_from_csv.py --gold-m15-csv "%GOLD_M15_CSV%" --gold-h1-csv "%GOLD_H1_CSV%" --btc-m5-csv "%BTC_M5_CSV%" --btc-m15-csv "%BTC_M15_CSV%" --btc-h1-csv "%BTC_H1_CSV%" --btc-h4-csv "%BTC_H4_CSV%" --history-csv "%HISTORY_CSV%" --gold-scan-recent-bars 60 --btc-scan-recent-m5-bars 60 --btc-scan-recent-m15-bars 20 --bar-offset 0 --btc-spread-mode csv_mode --btc-spread-source m5 --btc-point-size 0.01 --btc-pip-size 10 --enable-ai-review --send-discord

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Run finished: %DATE% %TIME%
echo Exit code: %EXIT_CODE%

if not "%EXIT_CODE%"=="0" (
    echo WARNING: portfolio notifier returned a non-zero exit code.
    echo The loop will continue at the next xx:01 slot.
)

goto LOOP

:WAIT_UNTIL_RUN_SECOND
powershell -NoProfile -ExecutionPolicy Bypass -Command "$runSecond = [int]$env:RUN_SECOND; $now = Get-Date; $target = $now.Date.AddHours($now.Hour).AddMinutes($now.Minute).AddSeconds($runSecond); if ($now -ge $target) { $target = $target.AddMinutes(1) }; $waitMs = [int][Math]::Max(0, [Math]::Ceiling(($target - $now).TotalMilliseconds)); Write-Host ('Waiting until ' + $target.ToString('HH:mm:ss') + '... Current time: ' + $now.ToString('HH:mm:ss.fff') + ' / wait_ms=' + $waitMs); Start-Sleep -Milliseconds $waitMs"
exit /b 0

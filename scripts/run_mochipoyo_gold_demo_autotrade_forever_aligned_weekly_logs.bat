@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyy"') do set LOG_YEAR=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format MM"') do set LOG_MONTH=%%I
for /f %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=Get-Date; $c=[Globalization.CultureInfo]::InvariantCulture; $w=$c.Calendar.GetWeekOfYear($d,[Globalization.CalendarWeekRule]::FirstFourDayWeek,[DayOfWeek]::Monday); 'week_{0:D2}' -f $w"') do set LOG_WEEK=%%I

set LOG_ROOT=data\runtime_logs\gold\%LOG_YEAR%\%LOG_MONTH%\%LOG_WEEK%\mochipoyo_gold
set OUT_DIR=%LOG_ROOT%\loop
set SUMMARY_CSV=%OUT_DIR%\gold_minimal_live_loop_live_summary.csv
set STOP_PREVIEW_TXT=%OUT_DIR%\loop_stopped_discord_preview.txt
set STOP_PREVIEW_JSON=%OUT_DIR%\loop_stopped_discord_preview.json

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo ============================================================
echo Mochipoyo GOLD demo autotrade FOREVER aligned runner
echo Weekly log layout / existing state ledgers stay fixed
echo LOG_ROOT=%LOG_ROOT%
echo OUT_DIR=%OUT_DIR%
echo Stop with Ctrl+C
echo ============================================================
echo.
echo Persistent state files used by existing Mochipoyo GOLD:
echo   trigger-state: data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv
echo   notification-ledger: data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv
echo   auto-trade-order-ledger: data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv
echo ============================================================

python scripts\run_mochipoyo_gold_minimal_live_loop_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --out-dir "%OUT_DIR%" ^
  --symbol GOLD ^
  --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv ^
  --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv ^
  --forever ^
  --align-to-second 2 ^
  --sleep-seconds 10 ^
  --commit-trigger-state ^
  --commit-ledger ^
  --discord-send ^
  --discord-max-rows 5 ^
  --discord-style compact ^
  --enable-order-payload-dry-run ^
  --order-broker-symbol GOLD# ^
  --order-fixed-lot 0.01 ^
  --order-magic 26050601 ^
  --order-max-rows 5 ^
  --enable-auto-trade-send ^
  --auto-trade-broker-symbol GOLD# ^
  --auto-trade-order-ledger-csv data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv ^
  --auto-trade-expected-login 75539039 ^
  --auto-trade-select-symbol ^
  --auto-trade-require-demo-account ^
  --auto-trade-position-policy block_any ^
  --auto-trade-max-symbol-positions 1 ^
  --auto-trade-max-symbol-lot 0.01 ^
  --auto-trade-max-orders 1 ^
  --stop-on-error

set EXIT_CODE=%ERRORLEVEL%

python scripts\notify_mochipoyo_loop_stopped.py ^
  --loop-name mochipoyo_gold_demo_autotrade_forever_aligned_weekly_logs ^
  --exit-code %EXIT_CODE% ^
  --summary-csv "%SUMMARY_CSV%" ^
  --preview-txt "%STOP_PREVIEW_TXT%" ^
  --preview-json "%STOP_PREVIEW_JSON%"

echo.
echo Finished with exit code %EXIT_CODE%.
echo Weekly log root: %LOG_ROOT%
echo Summary CSV: %SUMMARY_CSV%
echo Stop notification preview: %STOP_PREVIEW_TXT%
echo.
pause
exit /b %EXIT_CODE%

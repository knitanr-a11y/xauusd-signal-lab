@echo off
setlocal

rem Mochipoyo GOLD minimal live demo auto-trade forever loop, aligned to HH:MM:02.
rem
rem Safety:
rem - DEMO account only: expected login 75539039 + require-demo-account
rem - Broker symbol: GOLD#
rem - Fixed lot: 0.01
rem - Position policy: block_any, max 1 position / 0.01 lot
rem - Starts each Python iteration at second 02 of every minute
rem - MT5 ExportOhlcToCsv should export at second 00
rem - Do NOT run this together with run_mochipoyo_gold_minimal_live.bat
rem - If the loop stops with a non-zero exit code, Discord stop notification is sent.
rem
rem Before running:
rem - MT5 must be logged in to XMTrading demo account 75539039
rem - Algo Trading must be ON
rem - .env must contain the Discord webhook if Discord send / stop notification is used
rem - Confirm whether an existing GOLD# position is open. If open, auto-trade send will be blocked by block_any.

cd /d "%~dp0\.."

set SUMMARY_CSV=data\ml_loop_demo_prod_forever\gold_minimal_live_loop_live_summary.csv
set STOP_PREVIEW_TXT=data\ml_loop_demo_prod_forever\loop_stopped_discord_preview.txt
set STOP_PREVIEW_JSON=data\ml_loop_demo_prod_forever\loop_stopped_discord_preview.json

python scripts\run_mochipoyo_gold_minimal_live_loop_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --out-dir data\ml_loop_demo_prod_forever ^
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
  --loop-name mochipoyo_gold_demo_autotrade_forever_aligned ^
  --exit-code %EXIT_CODE% ^
  --summary-csv "%SUMMARY_CSV%" ^
  --preview-txt "%STOP_PREVIEW_TXT%" ^
  --preview-json "%STOP_PREVIEW_JSON%"

echo.
echo Finished with exit code %EXIT_CODE%.
echo Summary CSV: %SUMMARY_CSV%
echo Stop notification preview: %STOP_PREVIEW_TXT%
echo.
pause
exit /b %EXIT_CODE%

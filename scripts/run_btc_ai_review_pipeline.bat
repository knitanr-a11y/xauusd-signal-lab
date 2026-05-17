@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set OUT_DIR=data\runtime_logs\trade_ai_review_btc
set MQL5_FILES_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set BTC_MANUAL_LEDGER=data\r\btc_manual_demo_order_send_smoke_test\btc_manual_demo_order_ledger.csv
set BTC_SEND_ONCE_LEDGER=data\r\btc_manual_demo_order_send_smoke_test_send_once\btc_manual_demo_send_once_order_ledger.csv
set SUMMARY_JSON=%OUT_DIR%\btc_ai_review_pipeline_summary.json
set TAG_SUMMARY_CSV=%OUT_DIR%\trade_ai_tag_summary.csv

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo ============================================================
echo Unified BTC AI review pipeline
echo This BAT is read/evaluation only. It does not place orders.
echo It exports MT5 closed BTC history, builds outcome ledger, creates AI payloads,
echo runs AI review using .env OPENAI_API_KEY, and updates BTC tag summary.
echo OUT_DIR=%OUT_DIR%
echo BTC_MANUAL_LEDGER=%BTC_MANUAL_LEDGER%
echo BTC_SEND_ONCE_LEDGER=%BTC_SEND_ONCE_LEDGER%
echo TAG_SUMMARY_CSV=%TAG_SUMMARY_CSV%
echo NOTE: default BTC candle files are btc_m15.csv / btc_m5.csv / btc_h1.csv / btc_h4.csv / btc_d1.csv under MQL5 Files.
echo If your file names differ, run the .py directly with --m15-csv etc.
echo ============================================================

python scripts\run_btc_ai_review_pipeline.py ^
  --out-dir "%OUT_DIR%" ^
  --mql5-files-dir "%MQL5_FILES_DIR%" ^
  --order-ledger-csv "%BTC_MANUAL_LEDGER%" ^
  --order-ledger-csv "%BTC_SEND_ONCE_LEDGER%" ^
  --allow-missing-order-ledger ^
  --expected-login 75539039 ^
  --broker-symbols BTCUSD# ^
  --lookback-days 60 ^
  --model gpt-5-mini ^
  --min-sample 5

set EXITCODE=%ERRORLEVEL%

echo ============================================================
echo Unified BTC AI review pipeline exit code: %EXITCODE%
echo Summary JSON: %SUMMARY_JSON%
echo Tag summary CSV: %TAG_SUMMARY_CSV%
echo Outcome CSV: %OUT_DIR%\trade_outcome_ledger.csv
echo Review JSONL: %OUT_DIR%\trade_ai_review_ledger.jsonl
echo ============================================================
exit /b %EXITCODE%

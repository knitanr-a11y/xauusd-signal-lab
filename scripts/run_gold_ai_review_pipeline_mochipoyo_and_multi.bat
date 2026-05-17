@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set OUT_DIR=data\runtime_logs\trade_ai_review
set MQL5_FILES_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set MOCHIPOYO_LEDGER=data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv
set MULTI_LEDGER=data\runtime_state\gold\multi_strategy\guarded_demo_order_ledger.csv
set SUMMARY_JSON=%OUT_DIR%\gold_ai_review_pipeline_summary.json
set TAG_SUMMARY_CSV=%OUT_DIR%\trade_ai_tag_summary.csv

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo ============================================================
echo Unified GOLD AI review pipeline - Mochipoyo + multi-strategy
echo This BAT is read/evaluation only. It does not place orders.
echo It exports MT5 closed history, builds outcome ledger, creates AI payloads,
echo runs AI review using .env OPENAI_API_KEY, and updates tag summary.
echo OUT_DIR=%OUT_DIR%
echo MOCHIPOYO_LEDGER=%MOCHIPOYO_LEDGER%
echo MULTI_LEDGER=%MULTI_LEDGER%
echo TAG_SUMMARY_CSV=%TAG_SUMMARY_CSV%
echo ============================================================

python scripts\run_gold_ai_review_pipeline_mochipoyo_and_multi.py ^
  --out-dir "%OUT_DIR%" ^
  --mql5-files-dir "%MQL5_FILES_DIR%" ^
  --order-ledger-csv "%MOCHIPOYO_LEDGER%" ^
  --order-ledger-csv "%MULTI_LEDGER%" ^
  --allow-missing-order-ledger ^
  --expected-login 75539039 ^
  --broker-symbols GOLD# ^
  --lookback-days 60 ^
  --model gpt-5-mini ^
  --min-sample 5

set EXITCODE=%ERRORLEVEL%

echo ============================================================
echo Unified GOLD AI review pipeline exit code: %EXITCODE%
echo Summary JSON: %SUMMARY_JSON%
echo Tag summary CSV: %TAG_SUMMARY_CSV%
echo Outcome CSV: %OUT_DIR%\trade_outcome_ledger.csv
echo Review JSONL: %OUT_DIR%\trade_ai_review_ledger.jsonl
echo ============================================================
exit /b %EXITCODE%

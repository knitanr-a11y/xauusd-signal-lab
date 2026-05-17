@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set OUT_DIR=data\runtime_logs\trade_ai_review_btc
set MQL5_FILES_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set BTC_MULTI_LEDGER=data\runtime_state\btc\multi_strategy\guarded_demo_order_ledger.csv
set SUMMARY_JSON=%OUT_DIR%\btc_ai_review_pipeline_same_spec_summary.json
set TAG_SUMMARY_CSV=%OUT_DIR%\trade_ai_tag_summary.csv

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo ============================================================
echo BTC AI review pipeline - same spec as GOLD
 echo Evaluation only. No orders are placed by this BAT.
echo OUT_DIR=%OUT_DIR%
echo BTC_MULTI_LEDGER=%BTC_MULTI_LEDGER%
echo TAG_SUMMARY_CSV=%TAG_SUMMARY_CSV%
echo Candle defaults: btcusdsharp_m15/m5/h1/h4/d1.csv
echo Strategy fields are normalized before AI review.
echo ============================================================

python scripts\run_btc_ai_review_pipeline_same_spec.py ^
  --out-dir "%OUT_DIR%" ^
  --model gpt-5-mini ^
  --min-sample 5 ^
  -- ^
  --mql5-files-dir "%MQL5_FILES_DIR%" ^
  --order-ledger-csv "%BTC_MULTI_LEDGER%" ^
  --allow-missing-order-ledger ^
  --expected-login 75539039 ^
  --broker-symbols BTCUSD# ^
  --lookback-days 60

set EXITCODE=%ERRORLEVEL%

echo ============================================================
echo BTC AI review same-spec pipeline exit code: %EXITCODE%
echo Summary JSON: %SUMMARY_JSON%
echo Tag summary CSV: %TAG_SUMMARY_CSV%
echo Outcome CSV: %OUT_DIR%\trade_outcome_ledger.csv
echo Review JSONL: %OUT_DIR%\trade_ai_review_ledger.jsonl
echo ============================================================
exit /b %EXITCODE%

@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set ORDER_LEDGER=data\runtime_state\btc\strict_5\official_guarded_demo_order_ledger.csv
set OUT_DIR=data\runtime_logs\trade_ai_review_btc_strict_5_official
set NOT_USED_D1=data\runtime_state\btc\strict_5\NOT_USED_D1.csv

echo ============================================================
echo BTC strict 5 OFFICIAL post-trade AI review pipeline
echo Order ledger: %ORDER_LEDGER%
echo Output dir  : %OUT_DIR%
echo D1 csv      : NOT_USED
echo Safety      : No order_send / MT5 history read-only / AI hypothesis only
echo ============================================================

if not exist "%ORDER_LEDGER%" (
  echo [ERROR] Missing BTC strict 5 official order ledger:
  echo   %ORDER_LEDGER%
  echo Start guarded demo send first, or wait until at least one order payload is recorded.
  exit /b 2
)

python scripts\run_btc_ai_review_pipeline_same_spec.py ^
  --out-dir "%OUT_DIR%" ^
  --model gpt-5-mini ^
  --min-sample 5 ^
  -- ^
  --order-ledger-csv "%ORDER_LEDGER%" ^
  --broker-symbols BTCUSD# ^
  --expected-login 75539039 ^
  --lookback-days 60 ^
  --m15-file btcusdsharp_m15.csv ^
  --m5-file btcusdsharp_m5.csv ^
  --h1-file btcusdsharp_h1.csv ^
  --h4-file btcusdsharp_h4.csv ^
  --d1-csv "%NOT_USED_D1%"

set EXITCODE=%ERRORLEVEL%
echo BTC strict 5 official AI review pipeline exit code: %EXITCODE%
echo Summary JSON: %OUT_DIR%\btc_ai_review_pipeline_same_spec_summary.json
echo Tag summary : %OUT_DIR%\trade_ai_tag_summary.csv
exit /b %EXITCODE%

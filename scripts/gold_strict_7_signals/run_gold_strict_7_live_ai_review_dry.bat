@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 live AI review DRY
echo - post-trade AI review dry run
echo - pending-only review
echo - safe when order ledger does not exist yet
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_live_ai_review_safe.py ^
  --mql5-files-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --order-ledger-csv data\runtime_state\gold\strict_7\guarded_demo_order_ledger.csv ^
  --expected-login 75539039 ^
  --broker-symbols GOLD# ^
  --lookback-days 90 ^
  --model gpt-5-mini ^
  --dry-run

set EXIT_CODE=%ERRORLEVEL%
echo.
echo live AI review dry exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

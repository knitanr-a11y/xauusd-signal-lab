@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 guarded demo autotrade dry once
echo - builds strict 7 order payloads
echo - calls existing send_mt5_order_from_payload.py
echo - dry-run / order_check only
echo - no mt5.order_send
echo - no Discord send
echo - no AI call
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_guarded_demo_autotrade_from_csv.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --lot 0.01 ^
  --scan-recent-bars 3 ^
  --max-signal-age-minutes 15 ^
  --max-orders 1 ^
  --position-policy block_any ^
  --max-symbol-positions 1 ^
  --max-symbol-lot 0.01

set EXIT_CODE=%ERRORLEVEL%
echo.
echo guarded demo autotrade dry once exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

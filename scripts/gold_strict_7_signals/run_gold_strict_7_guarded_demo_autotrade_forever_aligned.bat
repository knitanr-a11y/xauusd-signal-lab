@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 guarded demo autotrade forever aligned
echo - mt5.order_send ENABLED through existing guarded sender
echo - aligned to every 5 minutes + 02 seconds
echo - lightweight candle tails
echo - expected-login and demo-account guard enabled
echo - duplicate prevention by guarded_demo_order_ledger.csv
echo - max-orders=1
echo - position-policy=block_any
echo - lot=0.01
echo - no Discord send
echo - no AI call
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_guarded_demo_autotrade_forever_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --send ^
  --allow-demo-send ^
  --interval-minutes 5 ^
  --run-delay-seconds 2 ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --lot 0.01 ^
  --scan-recent-bars 3 ^
  --max-signal-age-minutes 15 ^
  --tail-m5 2000 ^
  --tail-h1 1000 ^
  --tail-h4 500 ^
  --tail-d1 300 ^
  --max-orders 1 ^
  --position-policy block_any ^
  --max-symbol-positions 1 ^
  --max-symbol-lot 0.01

set EXIT_CODE=%ERRORLEVEL%
echo.
echo guarded demo autotrade forever loop stopped exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

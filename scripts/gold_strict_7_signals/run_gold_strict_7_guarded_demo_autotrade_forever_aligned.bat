@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD strict 7 guarded demo autotrade forever aligned
echo - mt5.order_send ENABLED through existing guarded sender
echo - aligned to every 1 minute + 05 seconds
echo - designed for delayed EA CSV writes; recommended EA InpExportSecond=2
echo - reads latest confirmed CSV row: bar_offset=0
echo - lightweight candle tails
echo - expected-login and demo-account guard enabled
echo - duplicate prevention by guarded_demo_order_ledger.csv
echo - max-orders=7
echo - position-policy=allow_any_until_max, same active magic is blocked by sender
echo - max-symbol-positions=7
echo - max-symbol-lot=0.07
echo - lot=0.01
echo - Python UTF-8 mode ENABLED to avoid cp932 print failures
echo - no Discord send
echo - no AI call
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_guarded_demo_autotrade_forever_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --send ^
  --allow-demo-send ^
  --interval-minutes 1 ^
  --run-delay-seconds 5 ^
  --broker-symbol GOLD# ^
  --expected-login 75539039 ^
  --lot 0.01 ^
  --scan-recent-bars 3 ^
  --max-signal-age-minutes 15 ^
  --bar-offset 0 ^
  --tail-m5 2000 ^
  --tail-h1 1000 ^
  --tail-h4 500 ^
  --tail-d1 300 ^
  --max-orders 7 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 7 ^
  --max-symbol-lot 0.07

set EXIT_CODE=%ERRORLEVEL%
echo.
echo guarded demo autotrade forever loop stopped exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

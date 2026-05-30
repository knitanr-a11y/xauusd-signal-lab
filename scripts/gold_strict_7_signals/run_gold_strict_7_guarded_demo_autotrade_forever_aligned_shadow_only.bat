@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD strict 7 guarded demo autotrade forever aligned SHADOW ONLY
echo - based on run_gold_strict_7_guarded_demo_autotrade_forever_aligned.bat
echo - same 1 minute + 05 seconds aligned cycle
echo - reads latest confirmed CSV row: bar_offset=0
echo - creates strict7 payloads using the existing guarded wrapper
echo - DOES NOT pass --send
echo - DOES NOT pass --allow-demo-send
echo - mt5.order_send DISABLED
echo - appends generated payloads to gold_strict7_shadow_signal_ledger.csv
echo - no Discord send
echo - no AI call
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_guarded_demo_autotrade_forever_aligned_shadow_only.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
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
  --max-symbol-lot 0.07 ^
  --shadow-ledger-csv data\runtime_state\gold\strict_7\gold_strict7_shadow_signal_ledger.csv ^
  --wrapper-out-dir data\verification\gold_strict7_shadow_payloads ^
  --loop-out-dir data\verification\gold_strict7_shadow_forever_loop ^
  --collect-out-root data\verification\gold_strict7_shadow_collect

set EXIT_CODE=%ERRORLEVEL%
echo.
echo shadow-only guarded demo autotrade forever loop stopped exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

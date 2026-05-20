@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 guarded demo autotrade loop dry once
echo - loop wrapper smoke test
echo - dry-run / order_check only when signal exists
echo - no mt5.order_send
echo - no Discord send
echo - no AI call
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_guarded_demo_autotrade_forever_aligned.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --run-immediately ^
  --max-iterations 1 ^
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
echo guarded demo autotrade loop dry once exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

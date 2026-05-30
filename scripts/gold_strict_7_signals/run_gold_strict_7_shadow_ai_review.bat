@echo off
setlocal
cd /d "%~dp0\..\.."

echo ============================================================
echo GOLD strict 7 shadow AI review
echo - evaluates paused / shadow-only strict7 signals
echo - settles virtual outcomes from M1 candles
echo - builds AI review payloads for resolved shadow trades only
echo - does NOT send MT5 orders
echo ============================================================

python scripts\gold_strict_7_signals\run_gold_strict_7_shadow_ai_review_pipeline.py ^
  --mql5-files-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --shadow-ledger-csv data\runtime_state\gold\strict_7\gold_strict7_shadow_signal_ledger.csv ^
  --m1-file goldsharp_m1.csv ^
  --m15-file goldsharp_m15.csv ^
  --m5-file goldsharp_m5.csv ^
  --h1-file goldsharp_h1.csv ^
  --h4-file goldsharp_h4.csv ^
  --d1-file goldsharp_d1.csv ^
  --horizon-minutes 1440 ^
  --inbar-priority SL ^
  --model gpt-5-mini

set EXIT_CODE=%ERRORLEVEL%
echo.
echo shadow AI review exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

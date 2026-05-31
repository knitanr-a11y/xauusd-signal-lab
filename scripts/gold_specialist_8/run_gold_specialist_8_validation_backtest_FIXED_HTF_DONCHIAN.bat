@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD specialist 8 validation backtest FIXED HTF DONCHIAN
echo - MT5 order_send DISABLED
echo - Discord send DISABLED
echo - AI call DISABLED
echo - fixes H1 Donchian context merge so all 8 candidate families can be detected
echo - output: data\gold_specialist_8\verification\backtests\YYYY\MM\YYYYMMDD_HHMMSS
echo - latest AI-review input: data\gold_specialist_8\verification\trade_outcomes\gold_specialist_8_validation_trade_outcome_ledger.csv
echo ============================================================

python scripts\gold_specialist_8\run_gold_specialist_8_validation_backtest_FIXED_HTF_DONCHIAN.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --out-root data\gold_specialist_8\verification\backtests ^
  --trade-outcome-dir data\gold_specialist_8\verification\trade_outcomes ^
  --m1-file goldsharp_m1.csv ^
  --m5-file goldsharp_m5.csv ^
  --m15-file goldsharp_m15.csv ^
  --h1-file goldsharp_h1.csv ^
  --h4-file goldsharp_h4.csv ^
  --d1-file goldsharp_d1.csv ^
  --horizon-minutes 2880 ^
  --base-lot 0.01 ^
  --max-lot 0.03 ^
  --sell-low-sl-max-lot 0.02

set EXIT_CODE=%ERRORLEVEL%
echo.
echo validation backtest FIXED HTF DONCHIAN exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

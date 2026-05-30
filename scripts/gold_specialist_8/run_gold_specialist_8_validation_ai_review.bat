@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD specialist 8 validation AI review
echo - reviews verification/backtest/shadow trade outcome CSV
echo - pending-only AI review
echo - hypothesis tags only; no strategy rule edits
echo - generated files: data\gold_specialist_8\verification\ai_review_validation\YYYY\MM\YYYYMMDD_HHMMSS
echo - persistent review ledger: data\gold_specialist_8\verification\ai_review_validation\trade_ai_review_ledger.jsonl
echo - safe when validation trade outcome CSV does not exist yet
echo ============================================================

python scripts\gold_specialist_8\run_gold_specialist_8_validation_ai_review_pipeline.py ^
  --trade-outcome-csv data\gold_specialist_8\verification\trade_outcomes\gold_specialist_8_validation_trade_outcome_ledger.csv ^
  --out-root data\gold_specialist_8\verification\ai_review_validation ^
  --review-ledger-jsonl data\gold_specialist_8\verification\ai_review_validation\trade_ai_review_ledger.jsonl ^
  --mql5-files-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --m15-file goldsharp_m15.csv ^
  --m5-file goldsharp_m5.csv ^
  --h1-file goldsharp_h1.csv ^
  --h4-file goldsharp_h4.csv ^
  --d1-file goldsharp_d1.csv ^
  --review-target all ^
  --model gpt-5-mini

set EXIT_CODE=%ERRORLEVEL%
echo.
echo validation AI review exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

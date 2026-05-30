@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set LOCK_DIR=data\gold_specialist_8\verification\ai_review_validation\.ai_review_lock

echo ============================================================
echo GOLD specialist 8 validation AI review SAFE GROUP 20
echo - reviews GROUP trades only, not components
echo - max-items=20 per run
echo - lock enabled to prevent duplicate concurrent API calls
echo - hypothesis tags only; no strategy rule edits
echo ============================================================

mkdir "%LOCK_DIR%" 2>nul
if errorlevel 1 (
  echo [ERROR] AI review lock already exists: %LOCK_DIR%
  echo [ERROR] Another AI review may still be running. Stop that process or delete the lock only after confirming it is stopped.
  pause
  exit /b 9
)

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
  --review-target group ^
  --model gpt-5-mini ^
  --max-items 20

set EXIT_CODE=%ERRORLEVEL%
rmdir "%LOCK_DIR%" 2>nul

echo.
echo validation AI review SAFE GROUP 20 exit_code=%EXIT_CODE%
pause
exit /b %EXIT_CODE%

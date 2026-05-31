@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set TRADE_OUTCOME_CSV=data\gold_specialist_8\verification\trade_outcomes\gold_specialist_8_validation_trade_outcome_ledger.csv
set OUT_ROOT=data\gold_specialist_8\verification\ai_review_validation
set REVIEW_LEDGER=data\gold_specialist_8\verification\ai_review_validation\trade_ai_review_ledger.jsonl
set LOCK_DIR=data\gold_specialist_8\verification\ai_review_validation\.gold_specialist_8_ai_review_REAL_GROUP20_LOCK

echo ============================================================
echo GOLD specialist 8 validation AI review REAL GROUP20 LOCKED
echo ============================================================
echo SPEC:
echo - REAL OpenAI API review: YES
echo - Review target: GROUP only
echo - Component review: DISABLED
echo - all review: DISABLED
echo - Max API items per run: 20
echo - Persistent ledger: %REVIEW_LEDGER%
echo - Lock: %LOCK_DIR%
echo - MT5 order_send: DISABLED
echo - Discord send: DISABLED
echo - Strategy rule edits: DISABLED
echo ============================================================

if not exist "%TRADE_OUTCOME_CSV%" (
  echo [ERROR] trade outcome CSV not found:
  echo %TRADE_OUTCOME_CSV%
  echo Run scripts\gold_specialist_8\run_gold_specialist_8_validation_backtest.bat first.
  pause
  exit /b 2
)

if exist "%REVIEW_LEDGER%\" (
  echo [ERROR] REVIEW_LEDGER path is a DIRECTORY, not a jsonl file:
  echo %REVIEW_LEDGER%
  echo Delete or rename that directory before running.
  pause
  exit /b 3
)

if not exist "%OUT_ROOT%" mkdir "%OUT_ROOT%"
if not exist "%REVIEW_LEDGER%" type nul > "%REVIEW_LEDGER%"

mkdir "%LOCK_DIR%" 2>nul
if errorlevel 1 (
  echo [ERROR] AI review lock already exists:
  echo %LOCK_DIR%
  echo Another AI review may still be running.
  echo If you are 100%% sure no review is running, delete the lock folder and retry.
  pause
  exit /b 9
)

for /f %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path '%TRADE_OUTCOME_CSV%'){(Import-Csv '%TRADE_OUTCOME_CSV%' ^| Where-Object {$_.review_target -eq 'group' -or $_.review_target_type -eq 'group'} ^| Measure-Object).Count}else{0}"') do set GROUP_ROWS=%%A
for /f %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path '%REVIEW_LEDGER%'){(Get-Content '%REVIEW_LEDGER%' ^| Where-Object {$_.Trim().Length -gt 0} ^| Measure-Object).Count}else{0}"') do set LEDGER_BEFORE=%%A

echo [PRECHECK] group rows in trade outcome CSV: !GROUP_ROWS!
echo [PRECHECK] review ledger rows before: !LEDGER_BEFORE!
echo [PRECHECK] this run will call API for at most 20 pending GROUP payloads.
echo.

python scripts\gold_specialist_8\run_gold_specialist_8_validation_ai_review_pipeline.py ^
  --trade-outcome-csv "%TRADE_OUTCOME_CSV%" ^
  --out-root "%OUT_ROOT%" ^
  --review-ledger-jsonl "%REVIEW_LEDGER%" ^
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

for /f %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path '%REVIEW_LEDGER%'){(Get-Content '%REVIEW_LEDGER%' ^| Where-Object {$_.Trim().Length -gt 0} ^| Measure-Object).Count}else{0}"') do set LEDGER_AFTER=%%A
set /a ADDED_ROWS=!LEDGER_AFTER!-!LEDGER_BEFORE!

rmdir "%LOCK_DIR%" 2>nul

echo.
echo ============================================================
echo RESULT
echo - exit_code: %EXIT_CODE%
echo - review ledger before: !LEDGER_BEFORE!
echo - review ledger after : !LEDGER_AFTER!
echo - newly written rows  : !ADDED_ROWS!
echo - latest run dir file : %OUT_ROOT%\latest_run_dir.txt
echo ============================================================

if not "%EXIT_CODE%"=="0" (
  echo [ERROR] AI review failed. Check the latest run summary JSON under %OUT_ROOT%.
)

pause
exit /b %EXIT_CODE%

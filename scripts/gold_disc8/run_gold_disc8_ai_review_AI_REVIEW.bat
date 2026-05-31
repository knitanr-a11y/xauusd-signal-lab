@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 AI review - REAL AI EXECUTION WITH PROGRESS
REM ==============================================================================
REM New clean DISC8 path version.
REM WARNING: This BAT calls OpenAI API for pending DISC8 sample payloads.
REM
REM MAX_PENDING=0 means all pending rows. Progress is written per row.
REM Successful rows are appended immediately to trade_ai_review_ledger.jsonl.
REM If interrupted, rerun this BAT; pending-only refresh skips completed rows.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "SAMPLE_CSV=data\gold_disc8\verification\ai_review_data_driven\latest_ai_review_sample_80_loss45.csv"
set "SAMPLE_AUDIT=data\gold_disc8\verification\ai_review_data_driven\latest_ai_review_sample_80_loss45_audit_summary.json"
set "OUT_DIR=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review"
set "LOG_DIR=data\gold_disc8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_disc8_ai_review_console.log"

set "M15_CSV="
set "M5_CSV="
set "H1_CSV="
set "H4_CSV="
set "D1_CSV="

REM 0 = all pending rows. Keep this for overnight full run.
set "MAX_PENDING=0"
set "MODEL=gpt-5-mini"
set "PROGRESS_EVERY=1"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

call :main > "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

type "%LOG_FILE%"
echo.
echo ==============================================================================
echo Console log saved to:
echo   %LOG_FILE%
echo exit_code=%EXIT_CODE%
echo ==============================================================================
echo.
pause
exit /b %EXIT_CODE%

:main
echo ==============================================================================
echo GOLD DISC8 AI review - REAL AI EXECUTION WITH PROGRESS
echo ==============================================================================
echo repo root    : %CD%
echo sample csv   : %SAMPLE_CSV%
echo sample audit : %SAMPLE_AUDIT%
echo out dir      : %OUT_DIR%
echo model        : %MODEL%
echo max pending  : %MAX_PENDING%
echo progress     : every %PROGRESS_EVERY% row(s)
echo AI API       : ENABLED
echo CSV mode     : auto-discover MQL5 Files or repo root goldsharp_*.csv
echo ==============================================================================
echo.

where python
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  exit /b 10
)
python --version
echo.

if not exist "%SAMPLE_CSV%" (
  echo [ERROR] sample csv not found.
  echo Expected: %SAMPLE_CSV%
  echo Run scripts\gold_disc8\run_gold_disc8_migrate_from_gold_specialist8_outputs.bat first,
  echo or run scripts\gold_disc8\run_gold_disc8_ai_review_sample_80_loss45_AUDIT_ONLY.bat.
  exit /b 11
)

if not exist "%SAMPLE_AUDIT%" (
  echo [ERROR] sample audit json not found.
  echo Expected: %SAMPLE_AUDIT%
  exit /b 12
)

python -c "import pandas as pd; print('pandas', pd.__version__); import openai; print('openai package ok')"
if errorlevel 1 (
  echo [ERROR] pandas/openai import failed.
  echo Install required packages in this Python environment.
  exit /b 13
)

echo.
echo [STEP 1] Refresh payloads and pending list without calling AI...
python scripts\gold_specialist_8\run_gold_data_driven_disc8_ai_review_pipeline.py ^
  --sample-csv "%SAMPLE_CSV%" ^
  --sample-audit-json "%SAMPLE_AUDIT%" ^
  --out-dir "%OUT_DIR%" ^
  --m15-csv "%M15_CSV%" ^
  --m5-csv "%M5_CSV%" ^
  --h1-csv "%H1_CSV%" ^
  --h4-csv "%H4_CSV%" ^
  --d1-csv "%D1_CSV%" ^
  --model "%MODEL%" ^
  --max-pending "%MAX_PENDING%"

set "PAYLOAD_EXIT=%ERRORLEVEL%"
echo payload_refresh_exit_code=%PAYLOAD_EXIT%
if not "%PAYLOAD_EXIT%"=="0" (
  echo [ERROR] Payload refresh failed. Do NOT run AI review.
  exit /b %PAYLOAD_EXIT%
)

echo.
echo [STEP 2] Run OpenAI review for pending payloads with per-row progress...
python scripts\gold_specialist_8\run_disc8_trade_ai_review_from_payloads_progress.py ^
  --payload-jsonl "%OUT_DIR%\trade_ai_review_payloads_pending.jsonl" ^
  --output-jsonl "%OUT_DIR%\trade_ai_review_ledger.jsonl" ^
  --output-json "%OUT_DIR%\trade_ai_review_run_summary.json" ^
  --model "%MODEL%" ^
  --progress-every "%PROGRESS_EVERY%"

set "AI_EXIT=%ERRORLEVEL%"
echo ai_review_exit_code=%AI_EXIT%
if not "%AI_EXIT%"=="0" (
  echo [ERROR] AI review runner reported errors. Already successful rows were still appended incrementally.
  echo Rerun this BAT after checking the log; pending-only refresh should skip completed rows.
  exit /b %AI_EXIT%
)

echo.
echo [STEP 3] Summarize AI tag ledger...
python scripts\summarize_trade_ai_review_ledger.py ^
  --trade-outcome-csv "%OUT_DIR%\disc8_review_trade_outcome_sample.csv" ^
  --ai-review-jsonl "%OUT_DIR%\trade_ai_review_ledger.jsonl" ^
  --output-csv "%OUT_DIR%\trade_ai_tag_summary.csv" ^
  --output-json "%OUT_DIR%\trade_ai_tag_summary.json" ^
  --min-sample 3 ^
  --include-open-trades

set "SUMMARY_EXIT=%ERRORLEVEL%"
echo summary_exit_code=%SUMMARY_EXIT%
if not "%SUMMARY_EXIT%"=="0" (
  echo [ERROR] Tag summary failed. AI review ledger may still be usable.
  exit /b %SUMMARY_EXIT%
)

echo Outputs:
echo   %OUT_DIR%\trade_ai_review_ledger.jsonl
echo   %OUT_DIR%\trade_ai_review_run_summary.json
echo   %OUT_DIR%\trade_ai_tag_summary.csv
echo   %OUT_DIR%\trade_ai_tag_summary.json
echo.
echo [OK] GOLD DISC8 AI review completed or no pending rows remained.
exit /b 0

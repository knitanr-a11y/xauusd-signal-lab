@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM DISC8 AI review - REAL AI EXECUTION
REM ==============================================================================
REM WARNING:
REM   This BAT calls OpenAI API for pending DISC8 sample payloads.
REM   It never reads full static_rule_trade_ledger.csv as review target.
REM   It uses only latest_ai_review_sample_80_loss45.csv.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "SAMPLE_CSV=data\gold_specialist_8\verification\ai_review_data_driven\latest_ai_review_sample_80_loss45.csv"
set "SAMPLE_AUDIT=data\gold_specialist_8\verification\ai_review_data_driven\latest_ai_review_sample_80_loss45_audit_summary.json"
set "OUT_DIR=data\gold_specialist_8\verification\ai_review_data_driven\disc8_ai_review"
set "LOG_DIR=data\gold_specialist_8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_disc8_ai_review_console.log"

REM Leave explicit CSV vars empty by default.
REM The Python pipeline will auto-discover candles in this order:
REM   1) MQL5 Files default folder + goldsharp_*.csv
REM   2) repo root + goldsharp_*.csv
REM If you want to force paths, fill these variables manually.
set "M15_CSV="
set "M5_CSV="
set "H1_CSV="
set "H4_CSV="
set "D1_CSV="

REM Safety: set MAX_PENDING to a small number for a smoke test, or 0 for all pending.
REM Example: set "MAX_PENDING=20"
set "MAX_PENDING=0"
set "MODEL=gpt-5-mini"

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
echo DISC8 AI review - REAL AI EXECUTION
echo ==============================================================================
echo repo root    : %CD%
echo sample csv   : %SAMPLE_CSV%
echo sample audit : %SAMPLE_AUDIT%
echo out dir      : %OUT_DIR%
echo model        : %MODEL%
echo max pending  : %MAX_PENDING%
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
  echo Run run_gold_data_driven_ai_review_sample_80_loss45_AUDIT_ONLY.bat first.
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
  --max-pending "%MAX_PENDING%" ^
  --run-ai

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] AI review pipeline failed or partial failure occurred. Check JSON summary and log.
  echo.
  echo If the error says M15 CSV not found, copy these files to the repo root or MQL5 Files folder:
  echo   goldsharp_m15.csv
  echo   goldsharp_m5.csv
  echo   goldsharp_h1.csv
  echo   goldsharp_h4.csv
  echo   goldsharp_d1.csv
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %OUT_DIR%\trade_ai_review_ledger.jsonl
echo   %OUT_DIR%\trade_ai_review_run_summary.json
echo   %OUT_DIR%\trade_ai_tag_summary.csv
echo   %OUT_DIR%\trade_ai_tag_summary.json
echo   %OUT_DIR%\gold_data_driven_disc8_ai_review_pipeline_summary.json
echo.
echo [OK] DISC8 AI review completed or no pending rows remained.
exit /b 0

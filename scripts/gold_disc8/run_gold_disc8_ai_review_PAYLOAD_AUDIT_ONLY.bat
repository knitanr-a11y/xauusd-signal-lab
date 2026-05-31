@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 AI review payload build - AUDIT ONLY / NO API
REM ==============================================================================
REM New clean DISC8 path version.
REM Builds feature snapshots and payload JSONL from fixed sample CSV.
REM Does NOT call OpenAI.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "SAMPLE_CSV=data\gold_disc8\verification\ai_review_data_driven\latest_ai_review_sample_80_loss45.csv"
set "SAMPLE_AUDIT=data\gold_disc8\verification\ai_review_data_driven\latest_ai_review_sample_80_loss45_audit_summary.json"
set "OUT_DIR=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review"
set "LOG_DIR=data\gold_disc8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_disc8_payload_audit_console.log"

set "M15_CSV="
set "M5_CSV="
set "H1_CSV="
set "H4_CSV="
set "D1_CSV="

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
echo GOLD DISC8 AI review payload build - AUDIT ONLY / NO API
echo ==============================================================================
echo repo root    : %CD%
echo sample csv   : %SAMPLE_CSV%
echo sample audit : %SAMPLE_AUDIT%
echo out dir      : %OUT_DIR%
echo AI API       : DISABLED
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

python -c "import pandas as pd; print('pandas', pd.__version__)"
if errorlevel 1 (
  echo [ERROR] pandas import failed.
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
  --model gpt-5-mini

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] DISC8 payload audit failed. Do NOT run AI review.
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %OUT_DIR%\disc8_review_trade_outcome_sample.csv
echo   %OUT_DIR%\trade_feature_snapshot.csv
echo   %OUT_DIR%\trade_feature_snapshot.jsonl
echo   %OUT_DIR%\trade_ai_review_payloads.jsonl
echo   %OUT_DIR%\trade_ai_review_payloads_pending.jsonl
echo   %OUT_DIR%\gold_data_driven_disc8_ai_review_pipeline_summary.json
echo.
echo [OK] DISC8 payload audit completed in data\gold_disc8. No OpenAI API call was made.
exit /b 0

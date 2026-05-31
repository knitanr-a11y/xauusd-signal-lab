@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 AI tag resummary ONLY
REM ==============================================================================
REM This BAT does NOT call OpenAI.
REM It only regenerates trade_ai_tag_summary.csv/json from existing
REM trade_ai_review_ledger.jsonl and DISC8 review sample outcome CSV.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "OUT_DIR=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review"
set "LOG_DIR=data\gold_disc8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_disc8_resummarize_ai_tags_console.log"

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
echo GOLD DISC8 AI tag resummary ONLY
echo ==============================================================================
echo repo root    : %CD%
echo out dir      : %OUT_DIR%
echo AI API       : DISABLED
echo ==============================================================================
echo.

where python
if errorlevel 1 (
  echo [ERROR] python command was not found in PATH.
  exit /b 10
)
python --version
echo.

if not exist "%OUT_DIR%\disc8_review_trade_outcome_sample.csv" (
  echo [ERROR] outcome sample csv not found:
  echo   %OUT_DIR%\disc8_review_trade_outcome_sample.csv
  exit /b 11
)

if not exist "%OUT_DIR%\trade_ai_review_ledger.jsonl" (
  echo [ERROR] AI review ledger not found:
  echo   %OUT_DIR%\trade_ai_review_ledger.jsonl
  exit /b 12
)

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
  echo [ERROR] Tag resummary failed.
  exit /b %SUMMARY_EXIT%
)

echo Outputs:
echo   %OUT_DIR%\trade_ai_tag_summary.csv
echo   %OUT_DIR%\trade_ai_tag_summary.json
echo.
echo [OK] DISC8 AI tag resummary completed. No OpenAI API call was made.
exit /b 0

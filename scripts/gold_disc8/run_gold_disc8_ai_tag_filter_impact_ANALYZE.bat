@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==============================================================================
REM GOLD DISC8 AI tag filter impact analysis
REM ==============================================================================
REM This BAT does NOT call OpenAI, MT5, or Discord.
REM It simulates excluding should_investigate AI tags and reports trade count,
REM monthly average, win rate, avg R, total R, and PF impact.
REM ==============================================================================

cd /d "%~dp0\..\.."

set "OUT_DIR=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review"
set "IMPACT_DIR=%OUT_DIR%\tag_filter_impact"
set "LOG_DIR=data\gold_disc8\verification\ai_review_data_driven"
set "LOG_FILE=%LOG_DIR%\latest_disc8_ai_tag_filter_impact_console.log"

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
echo GOLD DISC8 AI tag filter impact analysis
echo ==============================================================================
echo repo root    : %CD%
echo out dir      : %OUT_DIR%
echo impact dir   : %IMPACT_DIR%
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

if not exist "%OUT_DIR%\trade_ai_tag_summary.csv" (
  echo [ERROR] AI tag summary csv not found:
  echo   %OUT_DIR%\trade_ai_tag_summary.csv
  echo Run scripts\gold_disc8\run_gold_disc8_resummarize_ai_tags_ONLY.bat first.
  exit /b 13
)

python scripts\gold_disc8\analyze_gold_disc8_ai_tag_filter_impact.py ^
  --trade-outcome-csv "%OUT_DIR%\disc8_review_trade_outcome_sample.csv" ^
  --ai-review-jsonl "%OUT_DIR%\trade_ai_review_ledger.jsonl" ^
  --tag-summary-csv "%OUT_DIR%\trade_ai_tag_summary.csv" ^
  --output-dir "%IMPACT_DIR%" ^
  --large-drop-ratio 0.50 ^
  --min-remaining-ratio 0.50

set "PY_EXIT=%ERRORLEVEL%"
echo.
echo python_exit_code=%PY_EXIT%
echo.

if not "%PY_EXIT%"=="0" (
  echo [ERROR] DISC8 AI tag filter impact analysis failed.
  exit /b %PY_EXIT%
)

echo Outputs:
echo   %IMPACT_DIR%\disc8_ai_tag_filter_strategy_tag_individual_impact.csv
echo   %IMPACT_DIR%\disc8_ai_tag_filter_scenarios.csv
echo   %IMPACT_DIR%\disc8_ai_tag_filter_monthly_counts.csv
echo   %IMPACT_DIR%\disc8_ai_tag_filter_strategy_counts.csv
echo   %IMPACT_DIR%\disc8_ai_tag_filter_greedy_path.csv
echo   %IMPACT_DIR%\disc8_ai_tag_filter_excluded_trades.csv
echo   %IMPACT_DIR%\disc8_ai_tag_filter_impact_summary.json
echo.
echo [OK] DISC8 AI tag filter impact analysis completed. No OpenAI API call was made.
exit /b 0

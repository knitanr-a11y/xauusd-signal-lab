@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set AI_REVIEW_DIR=data\research_results\btc_strict_5_backtest_ai_review
set EXCLUSION_DIR=%AI_REVIEW_DIR%\ai_tag_exclusion_diagnostics
set NUMERIC_DIR=%AI_REVIEW_DIR%\ai_tag_numeric_condition_diagnostics
set SELECTED_CSV=%NUMERIC_DIR%\btc_strict_5_ai_tag_numeric_condition_selected_candidates.csv
set SUMMARY_CSV=%NUMERIC_DIR%\btc_strict_5_ai_tag_numeric_condition_summary.csv
set RULE_JSON=data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json
set RULE_CSV=data\runtime_state\btc\strict_5\ai_tag_numeric_rules_summary.csv

echo ============================================================
echo Build BTC strict 5 AI-tag numeric rules JSON
echo No AI call / No MT5 call / No Discord / No order_send
echo ============================================================

if not exist "%SELECTED_CSV%" if not exist "%SUMMARY_CSV%" (
  echo [INFO] Missing selected and summary condition CSV.
  echo [INFO] Building numeric condition diagnostics first...
  python scripts\btc_strict_5_signals\run_btc_strict_5_ai_tag_numeric_condition_diagnostics.py ^
    --ai-review-dir "%AI_REVIEW_DIR%" ^
    --exclusion-dir "%EXCLUSION_DIR%" ^
    --out-dir "%NUMERIC_DIR%"
  if errorlevel 1 (
    echo [ERROR] Failed to build numeric condition diagnostics.
    exit /b 1
  )
)

if exist "%SELECTED_CSV%" (
  set CONDITION_CSV=%SELECTED_CSV%
  echo [INFO] Using selected candidates CSV: %SELECTED_CSV%
) else if exist "%SUMMARY_CSV%" (
  set CONDITION_CSV=%SUMMARY_CSV%
  echo [INFO] selected candidates CSV not found. Using condition summary CSV: %SUMMARY_CSV%
) else (
  echo [ERROR] Missing both:
  echo   %SELECTED_CSV%
  echo   %SUMMARY_CSV%
  echo [ERROR] Check numeric condition diagnostics output above.
  exit /b 2
)

python scripts\btc_strict_5_signals\build_btc_strict_5_ai_tag_numeric_rules.py ^
  --condition-csv "%CONDITION_CSV%" ^
  --output-json "%RULE_JSON%" ^
  --output-csv "%RULE_CSV%"

set EXITCODE=%ERRORLEVEL%
echo Build BTC strict 5 AI-tag numeric rules exit code: %EXITCODE%
exit /b %EXITCODE%

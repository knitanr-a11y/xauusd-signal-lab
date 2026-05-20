@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set AI_REVIEW_DIR=data\research_results\btc_strict_5_backtest_ai_review
set EXCLUSION_DIR=%AI_REVIEW_DIR%\ai_tag_exclusion_diagnostics
set NUMERIC_DIR=%AI_REVIEW_DIR%\ai_tag_numeric_condition_diagnostics
set CONDITION_CSV=%NUMERIC_DIR%\btc_strict_5_ai_tag_numeric_condition_selected_candidates.csv
set RULE_JSON=data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json
set RULE_CSV=data\runtime_state\btc\strict_5\ai_tag_numeric_rules_summary.csv

echo ============================================================
echo Build BTC strict 5 AI-tag numeric rules JSON
echo No AI call / No MT5 call / No Discord / No order_send
echo ============================================================

if not exist "%CONDITION_CSV%" (
  echo [INFO] Missing %CONDITION_CSV%
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

if not exist "%CONDITION_CSV%" (
  echo [ERROR] Still missing %CONDITION_CSV%
  echo [ERROR] Check that backtest AI review and exclusion diagnostics are already complete.
  exit /b 2
)

python scripts\btc_strict_5_signals\build_btc_strict_5_ai_tag_numeric_rules.py ^
  --condition-csv "%CONDITION_CSV%" ^
  --output-json "%RULE_JSON%" ^
  --output-csv "%RULE_CSV%"

set EXITCODE=%ERRORLEVEL%
echo Build BTC strict 5 AI-tag numeric rules exit code: %EXITCODE%
exit /b %EXITCODE%

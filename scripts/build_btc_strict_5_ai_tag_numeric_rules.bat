@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ============================================================
echo Build BTC strict 5 AI-tag numeric rules JSON
echo No AI call / No MT5 call / No Discord / No order_send
echo ============================================================

python scripts\btc_strict_5_signals\build_btc_strict_5_ai_tag_numeric_rules.py ^
  --condition-csv data\research_results\btc_strict_5_backtest_ai_review\ai_tag_numeric_condition_diagnostics\btc_strict_5_ai_tag_numeric_condition_selected_candidates.csv ^
  --output-json data\runtime_state\btc\strict_5\ai_tag_numeric_rules.json ^
  --output-csv data\runtime_state\btc\strict_5\ai_tag_numeric_rules_summary.csv

set EXITCODE=%ERRORLEVEL%
echo Build BTC strict 5 AI-tag numeric rules exit code: %EXITCODE%
exit /b %EXITCODE%

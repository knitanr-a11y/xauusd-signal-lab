@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set AI_REVIEW_DIR=data\runtime_logs\trade_ai_review_backtest_gold_strict_7
set RULE_JSON=data\runtime_state\gold\strict_7\ai_tag_numeric_rules.json
set RULE_CSV=data\runtime_state\gold\strict_7\ai_tag_numeric_rules_summary.csv
set COMBO_CSV=data\runtime_state\gold\strict_7\ai_tag_combo_rules_summary.csv

echo ============================================================
echo Build GOLD strict 7 AI-tag numeric rules JSON
echo Input AI review dir: %AI_REVIEW_DIR%
echo Expected source: GOLD strict 7 backtest/post-trade AI review output
echo Output Rule JSON: %RULE_JSON%
echo Output Rule CSV : %RULE_CSV%
echo Output Combo CSV: %COMBO_CSV%
echo No AI call / No MT5 call / No Discord / No order_send
echo ============================================================

if not exist "%AI_REVIEW_DIR%\trade_feature_snapshot.csv" (
  echo [ERROR] Missing %AI_REVIEW_DIR%\trade_feature_snapshot.csv
  echo Run the GOLD strict 7 backtest/live post-trade AI review pipeline first.
  exit /b 2
)

if not exist "%AI_REVIEW_DIR%\trade_ai_review_ledger.jsonl" (
  echo [ERROR] Missing %AI_REVIEW_DIR%\trade_ai_review_ledger.jsonl
  echo Run the GOLD strict 7 backtest/live post-trade AI review pipeline first.
  exit /b 3
)

python scripts\gold_strict_7_signals\build_gold_strict_7_ai_tag_numeric_rules.py ^
  --ai-review-dir "%AI_REVIEW_DIR%" ^
  --output-json "%RULE_JSON%" ^
  --output-csv "%RULE_CSV%"

set EXITCODE=%ERRORLEVEL%
echo Build GOLD strict 7 single-tag numeric rules exit code: %EXITCODE%
if not "%EXITCODE%"=="0" (
  echo [ERROR] Single-tag numeric rule build failed. Combo rules were not generated.
  exit /b %EXITCODE%
)

python scripts\gold_strict_7_signals\add_gold_strict_7_ai_tag_combo_rules.py ^
  --ai-review-dir "%AI_REVIEW_DIR%" ^
  --rules-json "%RULE_JSON%" ^
  --output-csv "%COMBO_CSV%"

set EXITCODE=%ERRORLEVEL%
echo Add GOLD strict 7 AI-tag combo rules exit code: %EXITCODE%
echo Rule JSON: %RULE_JSON%
echo Rule CSV : %RULE_CSV%
echo Combo CSV: %COMBO_CSV%
exit /b %EXITCODE%

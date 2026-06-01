@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set AI_REVIEW_LEDGER_JSONL=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_ai_review_ledger.jsonl
set TRADE_FEATURE_SNAPSHOT_CSV=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv
set BASE_TRADE_CSV=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\disc8_review_trade_outcome_sample.csv
set KEPT_LEDGER_CSV=data\gold_disc8\source_of_truth\group_tag_filtered\group_tag_filtered_source_trade_ledger.csv
set GATE_RULES_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_runtime_group_tag_gate_rules.json
set OUT_DIR=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review

echo ============================================================
echo GOLD DISC8 AI-review numeric tagger builder
echo - Source of truth for tags: actual AI review JSONL
echo - Source of truth for features: trade_feature_snapshot.csv
echo - Audit only
echo - No OpenAI call
echo - No Discord send
echo - No MT5 order_send
echo - SOT mutation DISABLED
echo - runtime gate rules mutation DISABLED
echo - dispatch_ready DISABLED
echo ============================================================

if not exist "%AI_REVIEW_LEDGER_JSONL%" (
  echo [ERROR] Missing AI review ledger JSONL:
  echo   %AI_REVIEW_LEDGER_JSONL%
  echo This builder must use actual AI-review tags. It must not use hand-made proxy tags.
  pause
  exit /b 2
)

if not exist "%TRADE_FEATURE_SNAPSHOT_CSV%" (
  echo [ERROR] Missing trade feature snapshot CSV:
  echo   %TRADE_FEATURE_SNAPSHOT_CSV%
  pause
  exit /b 3
)

if not exist "%BASE_TRADE_CSV%" (
  echo [ERROR] Missing base 568 trade CSV:
  echo   %BASE_TRADE_CSV%
  pause
  exit /b 4
)

if not exist "%KEPT_LEDGER_CSV%" (
  echo [ERROR] Missing kept 292 SOT ledger:
  echo   %KEPT_LEDGER_CSV%
  pause
  exit /b 5
)

if not exist "%GATE_RULES_JSON%" (
  echo [ERROR] Missing runtime gate rules JSON:
  echo   %GATE_RULES_JSON%
  pause
  exit /b 6
)

python scripts\gold_disc8\build_gold_disc8_ai_tag_numeric_tagger_from_review.py ^
  --ai-review-ledger-jsonl "%AI_REVIEW_LEDGER_JSONL%" ^
  --trade-feature-snapshot-csv "%TRADE_FEATURE_SNAPSHOT_CSV%" ^
  --base-trade-csv "%BASE_TRADE_CSV%" ^
  --kept-ledger-csv "%KEPT_LEDGER_CSV%" ^
  --gate-rules-json "%GATE_RULES_JSON%" ^
  --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo DISC8 AI-review numeric tagger builder stopped exit_code=%EXIT_CODE%
echo Outputs:
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_build_summary.json
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_rules.json
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_rule_summary.csv
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_568_confusion_summary.csv
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_trade_audit.csv
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_proxy_tag_hits.csv
pause
exit /b %EXIT_CODE%

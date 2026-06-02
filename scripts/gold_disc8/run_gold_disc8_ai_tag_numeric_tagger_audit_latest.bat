@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set CANDIDATES_CSV=data\runtime_logs\gold_disc8_live_decision_audit\latest\gold_disc8_live_decision_candidates.csv
set DECISION_SUMMARY_JSON=data\runtime_logs\gold_disc8_live_decision_audit\latest\gold_disc8_live_decision_audit_summary.json
set RULES_JSON=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_rules.json
set TAG_RECALL_CSV=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv
set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set OUT_DIR=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_latest_audit\latest

echo ============================================================
echo GOLD DISC8 AI-review numeric tagger latest audit
echo - Uses numeric rules built from actual AI review tags
echo - Default: promotable tag subset only
echo - Audit only
echo - No OpenAI call
echo - No Discord send
echo - No MT5 order_send
echo - SOT mutation DISABLED
echo - runtime gate rules mutation DISABLED
echo - decision ledger mutation DISABLED
echo - dispatch_ready always false
echo ============================================================

if not exist "%CANDIDATES_CSV%" (
  echo [ERROR] Missing latest live decision candidates:
  echo   %CANDIDATES_CSV%
  echo Run scripts\gold_disc8\run_gold_disc8_live_decision_audit_forever_aligned.bat first.
  pause
  exit /b 2
)

if not exist "%RULES_JSON%" (
  echo [ERROR] Missing AI-review numeric tagger rules JSON:
  echo   %RULES_JSON%
  echo Run scripts\gold_disc8\run_gold_disc8_build_ai_tag_numeric_tagger_from_review.bat first.
  pause
  exit /b 3
)

if not exist "%CSV_DIR%\goldsharp_m15.csv" (
  echo [ERROR] Missing OHLC CSV:
  echo   %CSV_DIR%\goldsharp_m15.csv
  pause
  exit /b 4
)

python scripts\gold_disc8\apply_gold_disc8_ai_tag_numeric_tagger_audit_latest.py ^
  --candidates-csv "%CANDIDATES_CSV%" ^
  --decision-summary-json "%DECISION_SUMMARY_JSON%" ^
  --rules-json "%RULES_JSON%" ^
  --tag-recall-csv "%TAG_RECALL_CSV%" ^
  --csv-dir "%CSV_DIR%" ^
  --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo DISC8 AI-review numeric tagger latest audit stopped exit_code=%EXIT_CODE%
echo Outputs:
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_latest_audit_summary.json
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_latest_gate_audit.csv
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_latest_tag_hits.csv
echo   %OUT_DIR%\gold_disc8_ai_tag_numeric_tagger_latest_rule_eval_audit.csv
pause
exit /b %EXIT_CODE%

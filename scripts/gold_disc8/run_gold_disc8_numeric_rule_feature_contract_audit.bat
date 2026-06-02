@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set MANIFEST_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_operational_strategy_manifest.json
set RULES_JSON=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_rules.json
set TAG_RECALL_CSV=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv
set SOURCE_FEATURE_SNAPSHOT_CSV=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv
set OUT_DIR=data\runtime_logs\gold_disc8_numeric_rule_feature_contract_audit

echo ============================================================
echo GOLD DISC8 numeric rule feature contract audit
echo - Diagnoses why numeric tagger rules did or did not hit candidates
echo - Compares source feature snapshot vs live/backtest feature frame
echo - Audit only
echo - No OpenAI call
echo - No Discord send
echo - No MT5 order_send
echo - SOT mutation DISABLED
echo - runtime gate rules mutation DISABLED
echo - live decision ledger mutation DISABLED
echo ============================================================

if not exist "%RULES_JSON%" (
  echo [ERROR] Missing numeric rules JSON:
  echo   %RULES_JSON%
  echo Run scripts\gold_disc8\run_gold_disc8_build_ai_tag_numeric_tagger_from_review.bat first.
  pause
  exit /b 2
)

if not exist "%MANIFEST_JSON%" (
  echo [ERROR] Missing manifest JSON:
  echo   %MANIFEST_JSON%
  pause
  exit /b 3
)

if not exist "%CSV_DIR%\goldsharp_m15.csv" (
  echo [ERROR] Missing OHLC CSV:
  echo   %CSV_DIR%\goldsharp_m15.csv
  pause
  exit /b 4
)

python scripts\gold_disc8\audit_gold_disc8_numeric_rule_feature_contract.py ^
  --csv-dir "%CSV_DIR%" ^
  --manifest-json "%MANIFEST_JSON%" ^
  --rules-json "%RULES_JSON%" ^
  --tag-recall-csv "%TAG_RECALL_CSV%" ^
  --source-feature-snapshot-csv "%SOURCE_FEATURE_SNAPSHOT_CSV%" ^
  --out-dir "%OUT_DIR%" ^
  --max-bars 12000

set EXIT_CODE=%ERRORLEVEL%
echo.
echo DISC8 numeric rule feature contract audit stopped exit_code=%EXIT_CODE%
echo Outputs:
echo   %OUT_DIR%\gold_disc8_numeric_rule_feature_contract_audit_summary.json
echo   %OUT_DIR%\gold_disc8_numeric_rule_feature_contract_rule_audit.csv
echo   %OUT_DIR%\gold_disc8_numeric_rule_feature_contract_strategy_summary.csv
pause
exit /b %EXIT_CODE%

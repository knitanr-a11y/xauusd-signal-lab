@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_disc8\audit_gold_disc8_numeric_rule_feature_contract_v2.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
  --manifest-json "data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_operational_strategy_manifest.json" ^
  --rules-json "data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_rules.json" ^
  --tag-recall-csv "data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv" ^
  --source-feature-snapshot-csv "data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv" ^
  --out-dir "data\runtime_logs\gold_disc8_numeric_rule_feature_contract_audit" ^
  --max-bars 12000

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_numeric_rule_feature_contract_audit
pause
exit /b %EXIT_CODE%

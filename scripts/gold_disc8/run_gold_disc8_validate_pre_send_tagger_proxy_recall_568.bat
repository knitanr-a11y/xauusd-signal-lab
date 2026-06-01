@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set BASE_TRADE_CSV=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\disc8_review_trade_outcome_sample.csv
set KEPT_LEDGER_CSV=data\gold_disc8\source_of_truth\group_tag_filtered\group_tag_filtered_source_trade_ledger.csv
set RULE_HITS_CSV=data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\group_tag_filter_applied\safe\disc8_group_tag_filter_rule_hits.csv
set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set MANIFEST_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_operational_strategy_manifest.json
set GATE_RULES_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_runtime_group_tag_gate_rules.json
set OUT_DIR=data\runtime_logs\gold_disc8_pre_send_tagger_proxy_recall_568

echo ============================================================
echo GOLD DISC8 pre-send tagger proxy recall validation on 568 universe
echo - Audit only
echo - No OpenAI call
echo - No Discord send
echo - No MT5 order_send
echo - SOT mutation DISABLED
echo - runtime gate rules mutation DISABLED
echo - dispatch_ready always false
echo ============================================================

if not exist "%BASE_TRADE_CSV%" (
  echo [ERROR] Missing base 568 trade CSV:
  echo   %BASE_TRADE_CSV%
  echo This validation must use the original 568-trade universe, not the kept 292 SOT alone.
  pause
  exit /b 2
)

if not exist "%KEPT_LEDGER_CSV%" (
  echo [ERROR] Missing kept 292 SOT ledger:
  echo   %KEPT_LEDGER_CSV%
  pause
  exit /b 3
)

if not exist "%CSV_DIR%\goldsharp_m15.csv" (
  echo [ERROR] Missing OHLC CSV:
  echo   %CSV_DIR%\goldsharp_m15.csv
  pause
  exit /b 4
)

python scripts\gold_disc8\validate_gold_disc8_pre_send_tagger_proxy_recall_568.py ^
  --base-trade-csv "%BASE_TRADE_CSV%" ^
  --kept-ledger-csv "%KEPT_LEDGER_CSV%" ^
  --rule-hits-csv "%RULE_HITS_CSV%" ^
  --csv-dir "%CSV_DIR%" ^
  --manifest-json "%MANIFEST_JSON%" ^
  --gate-rules-json "%GATE_RULES_JSON%" ^
  --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo 568 proxy recall validation stopped exit_code=%EXIT_CODE%
echo Outputs:
echo   %OUT_DIR%\gold_disc8_proxy_recall_568_summary.json
echo   %OUT_DIR%\gold_disc8_proxy_recall_568_confusion_summary.csv
echo   %OUT_DIR%\gold_disc8_proxy_recall_568_strategy_confusion_summary.csv
echo   %OUT_DIR%\gold_disc8_proxy_recall_568_tag_recall_summary.csv
echo   %OUT_DIR%\gold_disc8_proxy_recall_568_trade_audit.csv
echo   %OUT_DIR%\gold_disc8_proxy_recall_568_proxy_tag_hits.csv
pause
exit /b %EXIT_CODE%

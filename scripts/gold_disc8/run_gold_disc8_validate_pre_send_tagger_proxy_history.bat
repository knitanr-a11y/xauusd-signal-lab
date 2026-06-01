@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set LEDGER_CSV=data\gold_disc8\source_of_truth\group_tag_filtered\group_tag_filtered_source_trade_ledger.csv
set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set MANIFEST_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_operational_strategy_manifest.json
set GATE_RULES_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_runtime_group_tag_gate_rules.json
set OUT_DIR=data\runtime_logs\gold_disc8_pre_send_tagger_proxy_history_validation

echo ============================================================
echo GOLD DISC8 pre-send tagger proxy historical validation
echo - Audit only
echo - No OpenAI call
echo - No Discord send
echo - No MT5 order_send
echo - dispatch_ready always false
echo - validates proxy BLOCK/ALLOW behavior on historical source-of-truth trades
echo ============================================================

if not exist "%LEDGER_CSV%" (
  echo [ERROR] Missing source trade ledger:
  echo   %LEDGER_CSV%
  echo Run scripts\gold_disc8\run_gold_disc8_freeze_group_tag_filtered_source_of_truth.bat first.
  pause
  exit /b 2
)

if not exist "%CSV_DIR%\goldsharp_m15.csv" (
  echo [ERROR] Missing live/historical M15 CSV:
  echo   %CSV_DIR%\goldsharp_m15.csv
  pause
  exit /b 3
)

if not exist "%MANIFEST_JSON%" (
  echo [ERROR] Missing operational manifest:
  echo   %MANIFEST_JSON%
  pause
  exit /b 4
)

if not exist "%GATE_RULES_JSON%" (
  echo [ERROR] Missing runtime gate rules:
  echo   %GATE_RULES_JSON%
  pause
  exit /b 5
)

python scripts\gold_disc8\validate_gold_disc8_pre_send_tagger_proxy_history.py ^
  --ledger-csv "%LEDGER_CSV%" ^
  --csv-dir "%CSV_DIR%" ^
  --manifest-json "%MANIFEST_JSON%" ^
  --gate-rules-json "%GATE_RULES_JSON%" ^
  --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo pre-send tagger proxy historical validation stopped exit_code=%EXIT_CODE%
echo Outputs:
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_proxy_history_validation_summary.json
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_proxy_history_gate_impact_summary.csv
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_proxy_history_strategy_gate_summary.csv
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_proxy_history_tag_impact_summary.csv
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_proxy_history_trade_audit.csv
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_proxy_history_tag_hits.csv
pause
exit /b %EXIT_CODE%

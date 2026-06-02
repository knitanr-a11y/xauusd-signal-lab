@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set CSV_DIR=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
set MANIFEST_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_operational_strategy_manifest.json
set NUMERIC_RULES_JSON=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_rules.json
set TAG_RECALL_CSV=data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv
set OUT_ROOT=data\runtime_logs\gold_disc8_backtest_live_decision_numeric_tagger_audit

echo ============================================================
echo GOLD DISC8 backtest live-decision + AI numeric tagger audit
echo - Replays current live decision logic over historical OHLC
echo - Applies AI-review numeric tagger rules
echo - Audit only
echo - No OpenAI call
echo - No Discord send
echo - No MT5 order_send
echo - SOT mutation DISABLED
echo - runtime gate rules mutation DISABLED
echo - live decision ledger mutation DISABLED
echo - dispatch_ready always false
echo - Outputs use run_id folder; latest is analysis copy only
echo ============================================================

if not exist "%CSV_DIR%\goldsharp_m15.csv" (
  echo [ERROR] Missing OHLC CSV:
  echo   %CSV_DIR%\goldsharp_m15.csv
  pause
  exit /b 2
)

if not exist "%CSV_DIR%\goldsharp_h1.csv" (
  echo [ERROR] Missing OHLC CSV:
  echo   %CSV_DIR%\goldsharp_h1.csv
  pause
  exit /b 3
)

if not exist "%MANIFEST_JSON%" (
  echo [ERROR] Missing operational strategy manifest:
  echo   %MANIFEST_JSON%
  pause
  exit /b 4
)

if not exist "%NUMERIC_RULES_JSON%" (
  echo [ERROR] Missing AI-review numeric tagger rules JSON:
  echo   %NUMERIC_RULES_JSON%
  echo Run scripts\gold_disc8\run_gold_disc8_build_ai_tag_numeric_tagger_from_review.bat first.
  pause
  exit /b 5
)

python scripts\gold_disc8\backtest_gold_disc8_live_decision_numeric_tagger_audit.py ^
  --csv-dir "%CSV_DIR%" ^
  --manifest-json "%MANIFEST_JSON%" ^
  --numeric-rules-json "%NUMERIC_RULES_JSON%" ^
  --tag-recall-csv "%TAG_RECALL_CSV%" ^
  --out-root "%OUT_ROOT%" ^
  --max-bars 12000 ^
  --outcome-lower-tf-file goldsharp_m5.csv ^
  --outcome-horizon-minutes 2880

set EXIT_CODE=%ERRORLEVEL%
echo.
echo DISC8 backtest audit stopped exit_code=%EXIT_CODE%
echo Outputs latest analysis copy:
echo   %OUT_ROOT%\latest\gold_disc8_backtest_audit_summary.json
echo   %OUT_ROOT%\latest\gold_disc8_backtest_overall_summary.csv
echo   %OUT_ROOT%\latest\gold_disc8_backtest_monthly_summary.csv
echo   %OUT_ROOT%\latest\gold_disc8_backtest_strategy_summary.csv
echo   %OUT_ROOT%\latest\gold_disc8_backtest_numeric_gate_audit.csv
echo   %OUT_ROOT%\latest\gold_disc8_backtest_live_candidates.csv
echo.
echo Important: latest is NOT an operational ledger. Run-specific immutable output is under:
echo   %OUT_ROOT%\runs\[run_id]\
pause
exit /b %EXIT_CODE%

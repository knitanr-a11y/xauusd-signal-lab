@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD DISC8 AI_BLOCK_AND_NUMERIC_ALLOW miss analysis audit
echo ============================================================
echo.
echo Purpose:
echo   Analyze the 200 AI_BLOCK trades missed by numeric gate.
echo   This is audit-only. No OpenAI, Discord, MT5, SOT mutation, or runtime promotion.
echo.
echo Input SOT:
echo   data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv
echo.
echo Optional feature probe source:
echo   data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv
echo.
echo Outputs:
echo   data\runtime_logs\gold_disc8_ai_block_numeric_miss_analysis_568\latest
echo.
echo Safety:
echo   dispatch_ready must remain false.
echo   Probe rows are NOT runtime rules.
echo.

python scripts\gold_disc8\audit_gold_disc8_ai_block_numeric_miss_analysis_568.py ^
  --trade-audit-csv "data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv" ^
  --trade-feature-snapshot-csv "data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv" ^
  --out-root "data\runtime_logs\gold_disc8_ai_block_numeric_miss_analysis_568" ^
  --expected-trade-rows 568 ^
  --min-tag-rows 5 ^
  --min-feature-non-null 5 ^
  --max-probe-rows-per-tag 10

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_ai_block_numeric_miss_analysis_568\latest
pause
exit /b %EXIT_CODE%

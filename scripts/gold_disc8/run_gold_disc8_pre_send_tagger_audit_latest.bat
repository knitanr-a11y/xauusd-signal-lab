@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set CANDIDATES_CSV=data\runtime_logs\gold_disc8_live_decision_audit\latest\gold_disc8_live_decision_candidates.csv
set DECISION_SUMMARY_JSON=data\runtime_logs\gold_disc8_live_decision_audit\latest\gold_disc8_live_decision_audit_summary.json
set GATE_RULES_JSON=data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_runtime_group_tag_gate_rules.json
set OUT_DIR=data\runtime_logs\gold_disc8_pre_send_tagger_audit\latest

echo ============================================================
echo GOLD DISC8 pre-send tagger audit latest
echo - PROVISIONAL tagger audit only
echo - Discord send DISABLED
echo - MT5 order_send DISABLED
echo - OpenAI call DISABLED
echo - decision ledger mutation DISABLED
echo - dispatch_ready always forced false
echo ============================================================

if not exist "%CANDIDATES_CSV%" (
  echo [ERROR] Missing latest DISC8 decision candidates CSV:
  echo   %CANDIDATES_CSV%
  echo Run scripts\gold_disc8\run_gold_disc8_live_decision_audit_forever_aligned.bat first.
  pause
  exit /b 2
)

if not exist "%DECISION_SUMMARY_JSON%" (
  echo [ERROR] Missing latest DISC8 decision summary JSON:
  echo   %DECISION_SUMMARY_JSON%
  pause
  exit /b 3
)

if not exist "%GATE_RULES_JSON%" (
  echo [ERROR] Missing runtime gate rules JSON:
  echo   %GATE_RULES_JSON%
  pause
  exit /b 4
)

python scripts\gold_disc8\apply_gold_disc8_pre_send_tagger_audit_latest.py ^
  --candidates-csv "%CANDIDATES_CSV%" ^
  --decision-summary-json "%DECISION_SUMMARY_JSON%" ^
  --gate-rules-json "%GATE_RULES_JSON%" ^
  --out-dir "%OUT_DIR%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo pre-send tagger audit latest stopped exit_code=%EXIT_CODE%
echo Outputs:
echo   %OUT_DIR%\gold_disc8_pre_send_tag_hits.csv
echo   %OUT_DIR%\gold_disc8_pre_send_gate_audit.csv
echo   %OUT_DIR%\gold_disc8_pre_send_tagger_audit_summary.json
pause
exit /b %EXIT_CODE%

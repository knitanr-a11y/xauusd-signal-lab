@echo off
setlocal enabledelayedexpansion

REM GOLD V3 13 ranking decision template audit-only.
REM This BAT creates ranking/decision template outputs only.
REM It does not approve, replay, train, generate signals, create ZIP output,
REM call AI API, notify Discord, place MT5 orders, or enable live hooks/evaluators.

cd /d "%~dp0"

echo [GOLD_V3_13] audit-only ranking decision template
echo [GOLD_V3_13] external actions remain OFF: Discord=false MT5=false AI_API=false live_hook=false live_evaluator=false final_signal=false
echo [GOLD_V3_13] prohibited: final approval, threshold finalization, replay, model training, signal generation, ZIP output

python scripts\gold_v3_13_ranking_decision_template_audit_only.py --repo-root "%CD%"
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_13] BLOCKED or FAILED. Check Files\FX_OUTPUTS\gold_v3\13_ranking_decision_template_audit_only\gold_v3_13_summary.json
  exit /b %EXIT_CODE%
)

echo [GOLD_V3_13] READY audit-only. No approval/live/replay action was performed.
exit /b 0

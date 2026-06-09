@echo off
setlocal

cd /d "%~dp0..\..\.."
if errorlevel 1 (
  echo [GOLD_V3_13] ERROR: could not move to repository root.
  exit /b 1
)

echo [GOLD_V3_13] audit-only ranking decision template
echo [GOLD_V3_13] repo_root=%CD%
echo [GOLD_V3_13] script=scripts\gold_v3_runtime\gold_v3_13_ranking_decision_template_audit_only.py
echo [GOLD_V3_13] stage 13 does not approve, replay, train, signal, zip, or call external integrations.

python scripts\gold_v3_runtime\gold_v3_13_ranking_decision_template_audit_only.py --repo-root "%CD%"
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo [GOLD_V3_13] BLOCKED or FAILED. Check Files\FX_OUTPUTS\gold_v3\13_ranking_decision_template_audit_only\gold_v3_13_summary.json
  echo [GOLD_V3_13] If exception occurred, check Files\FX_OUTPUTS\gold_v3\13_ranking_decision_template_audit_only\gold_v3_13_exception.txt
  exit /b %EXIT_CODE%
)

echo [GOLD_V3_13] READY audit-only.
exit /b 0

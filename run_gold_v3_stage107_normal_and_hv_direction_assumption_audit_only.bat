@echo off
setlocal

REM GOLD V3 Stage107 audit-only runner.
REM Absolute guardrails:
REM - Do not use GOLD V2 / old GOLD / DISC8 / Stage41 as trading source.
REM - Do not mutate CSVs, candidate pool, Stage45, Stage69, runtime, live evaluator, or final signal.
REM - CSV latest row is contractually closed; do not treat it as open/as-of.

cd /d "%~dp0"

if not exist "reports\gold_v3\stage107" mkdir "reports\gold_v3\stage107"

python "scripts\gold_v3_stage107_normal_and_hv_direction_assumption_audit_only.py" ^
  --out-dir "reports\gold_v3\stage107"

set EXITCODE=%ERRORLEVEL%

echo.
echo Stage107 finished with exit code %EXITCODE%.
echo Expected artifacts:
echo   reports\gold_v3\stage107\gold_v3_107_direction_assumption_summary.json
echo   reports\gold_v3\stage107\GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md
echo.
if not "%EXITCODE%"=="0" (
  echo Stage107 may be BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN.
  echo Open the report above before taking any next action.
)

exit /b %EXITCODE%

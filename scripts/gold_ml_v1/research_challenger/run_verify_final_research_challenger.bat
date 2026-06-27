@echo off
setlocal
cd /d "%~dp0\..\..\..\.."
py -3.12 scripts\gold_ml_v1\research_challenger\verify_final_research_challenger.py
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Final research challenger parity FAILED. Exit code: %EXIT_CODE%
  echo Confirm that the 15 frozen artifacts from the delivered local audit ZIP exist under:
  echo config\gold_ml_v1\research_challenger\final_20260627\artifacts
  exit /b %EXIT_CODE%
)
echo.
echo Final research challenger parity PASSED.
exit /b 0
